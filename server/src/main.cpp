#include <libplatform/libplatform.h>
#include <pybind11/embed.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <v8.h>

#include <iostream>
#include <list>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace py = pybind11;

/**
 * V8System class that encapsulates the v8 runtime
 * stateful/instantiated when the embedding app is started up,
 * torn down on app shutdown
 */
class V8System {
   public:
    /**
     * constructor that initializes v8 and the platform
     */
    V8System() {
        platform_ = v8::platform::NewDefaultPlatform();
        v8::V8::InitializePlatform(platform_.get());
        v8::V8::Initialize();
        logging_ = py::module::import("logging");
        logger_ = logging_.attr("getLogger")("uvicorn.error");
        logger_.attr("info")("V8 initialized");
    }

    /**
     * takes a script source code and compiles it+runs it
     */
    static std::string compile_and_invoke_source(const std::string& src) {
        // create a new isolate
        v8::Isolate::CreateParams create_params;
        create_params.array_buffer_allocator =
            v8::ArrayBuffer::Allocator::NewDefaultAllocator();
        // custom deleter for the isolate - dispose when the unique_ptr goes out
        // of scope
        std::unique_ptr<v8::Isolate, decltype(&dispose_isolate)> isolate(
            v8::Isolate::New(create_params), dispose_isolate);
        v8::Isolate::Scope isolate_scope(isolate.get());
        v8::HandleScope handle_scope(isolate.get());
        v8::Local<v8::Context> context = v8::Context::New(isolate.get());
        v8::Context::Scope context_scope(context);
        v8::TryCatch try_catch(isolate.get());
        auto source = to_v8_string(isolate.get(), src);
        auto maybe_module = compile_module(source, context);
        if (maybe_module.IsEmpty()) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        auto module = maybe_module.ToLocalChecked();
        if (!module->InstantiateModule(context, nullptr).FromMaybe(false)) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        if (module->Evaluate(context).IsEmpty()) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        return call_default_export(isolate.get(), context, module);
    }

    /**
     * if there is a warm isolate in the cache for this function,
     * use it to call the function. otherwise, create a new isolate
     */
    std::string invoke_function(
        const std::string& function_id, const std::string& source,
        const std::optional<py::dict>& payload = std::nullopt) {
        if (payload) {
            logger_.attr("info")("invoking function: " + function_id +
                                 " with payload: " +
                                 py::str(payload.value()).cast<std::string>());
        } else {
            logger_.attr("info")("invoking function: " + function_id);
        }
        {
            auto* warm_function = get_warm_function_from_pool(function_id);
            if (warm_function) {
                auto* warm_isolate = warm_function->isolate;
                // we have a cached isolate. use it to invoke the function
                logger_.attr("info")("isolate pool hit for function: " +
                                     function_id);
                v8::Isolate::Scope isolate_scope(warm_isolate);
                v8::HandleScope handle_scope(warm_isolate);
                v8::Local<v8::Context> context = v8::Context::New(warm_isolate);
                v8::Context::Scope context_scope(context);
                v8::Local<v8::Module> warm_mod =
                    warm_function->mod.Get(warm_isolate);
                return call_default_export(warm_isolate, context, warm_mod);
            }
        }
        logger_.attr("info")("isolate pool miss for function: " + function_id);
        // we don't have a cached isolate. create one and put it in the cache
        v8::Isolate::CreateParams create_params;
        create_params.array_buffer_allocator =
            v8::ArrayBuffer::Allocator::NewDefaultAllocator();
        v8::Isolate* isolate = v8::Isolate::New(create_params);
        v8::Isolate::Scope isolate_scope(isolate);
        v8::HandleScope handle_scope(isolate);
        v8::Local<v8::Context> context = v8::Context::New(isolate);
        v8::Context::Scope context_scope(context);
        v8::TryCatch try_catch(isolate);
        auto source_code = to_v8_string(isolate, source);
        auto mod = compile_and_evaluate_module(source_code, context);
        auto result = call_default_export(isolate, context, mod);
        logger_.attr("info")("putting warm isolate in pool for function: " +
                             function_id);
        put_warm_function_to_pool(function_id, isolate, mod);
        logger_.attr("info")("warm isolate put in pool for function: " +
                             function_id);
        return result;
    }

   private:
    /**
     * struct to hold the warm isolate and the compiled/evaluated module
     * subsequent invocations for a warm function just call the default export
     * of the compiled/evaluated module
     */
    struct WarmFunction {
        v8::Isolate* isolate;
        v8::Global<v8::Module> mod;

        WarmFunction(v8::Isolate* isolate, v8::Local<v8::Module> mod)
            : isolate(isolate), mod(isolate, mod) {}
    };

    /**
     * v8 platform instance. this needs to be kept alive for the lifetime of the
     * class instance
     */
    std::unique_ptr<v8::Platform> platform_;
    /**
     * pool of warm isolates
     */
    int pool_capacity_ = 128;
    std::list<std::pair<std::string, WarmFunction*>> pool_cache_;
    std::unordered_map<
        std::string,
        typename std::list<std::pair<std::string, WarmFunction*>>::iterator>
        pool_lookup_;
    /**
     * python logging module and logger instance
     */
    py::object logging_;
    py::object logger_;

    WarmFunction* get_warm_function_from_pool(const std::string& function_id) {
        auto it = pool_lookup_.find(function_id);
        if (it != pool_lookup_.end()) {
            auto& entry = it->second->second;
            return entry;
        }
        return nullptr;
    }

    void put_warm_function_to_pool(const std::string& function_id,
                                   v8::Isolate* isolate,
                                   v8::Local<v8::Module> mod) {
        if (pool_cache_.size() >= pool_capacity_) {
            auto& entry = pool_cache_.back();
            auto key = std::get<0>(entry);
            logging_.attr("info")("evicting isolate for function: " + key);
            auto* warm = std::get<1>(entry);
            dispose_isolate(warm->isolate);
            warm->mod.Reset();
            pool_lookup_.erase(key);
            pool_cache_.pop_back();
        }
        pool_cache_.emplace_front(function_id, new WarmFunction(isolate, mod));
        pool_lookup_[function_id] = pool_cache_.begin();
    }

    /**
     * load a module from source code in the given context
     */
    static v8::MaybeLocal<v8::Module> compile_module(
        v8::Local<v8::String> code, v8::Local<v8::Context> cx) {
        // compile the module
        v8::ScriptOrigin origin(to_v8_string(cx->GetIsolate(), "module"), 0, 0,
                                false, -1, v8::Local<v8::Value>(), false, false,
                                true, v8::Local<v8::PrimitiveArray>());
        v8::ScriptCompiler::Source source(code, origin);
        auto res = v8::ScriptCompiler::CompileModule(cx->GetIsolate(), &source);
        return res;
    }

    static v8::Local<v8::Module> compile_and_evaluate_module(
        v8::Local<v8::String> source, v8::Local<v8::Context> context) {
        auto* isolate = context->GetIsolate();
        v8::TryCatch try_catch(isolate);
        auto maybe_module = compile_module(source, context);
        if (maybe_module.IsEmpty()) {
            throw_runtime_error(isolate, try_catch.Exception());
        }
        auto mod = maybe_module.ToLocalChecked();
        if (!mod->InstantiateModule(context, nullptr).FromMaybe(false)) {
            throw_runtime_error(isolate, try_catch.Exception());
        }
        if (mod->Evaluate(context).IsEmpty()) {
            throw_runtime_error(isolate, try_catch.Exception());
        }
        return mod;
    }

    /**
     * takes a compiled esm module and calls the default (async) export. ie:
     * ```js
     * export default async function() {
     *  return "hello world";
     * }
     * ```
     */
    static std::string call_default_export(v8::Isolate* isolate,
                                           v8::Local<v8::Context> context,
                                           v8::Local<v8::Module> module) {
        // get the default export from the module
        v8::Local<v8::Value> namespace_object = module->GetModuleNamespace();
        if (!namespace_object->IsObject()) {
            throw std::runtime_error("module namespace is not an object");
        }
        v8::Local<v8::Object> ns_object = namespace_object.As<v8::Object>();
        auto maybe_default_export =
            ns_object->Get(context, to_v8_string(isolate, "default"));
        if (maybe_default_export.IsEmpty()) {
            throw std::runtime_error("default export is empty");
        }
        auto default_export = maybe_default_export.ToLocalChecked();
        if (!default_export->IsAsyncFunction()) {
            throw std::runtime_error(
                "default export is not an async function. got: " +
                std::string(*v8::String::Utf8Value(isolate, default_export)));
        }
        // call the default export
        auto func = default_export.As<v8::Function>();
        auto maybe_promise = func->Call(context, context->Global(), 0, nullptr);
        if (maybe_promise.IsEmpty()) {
            throw std::runtime_error("failed to call the default export");
        }
        auto promise = maybe_promise.ToLocalChecked();
        if (!promise->IsPromise()) {
            throw std::runtime_error("return value is not a promise");
        }
        // wait for the promise to resolve
        auto result = promise.As<v8::Promise>()->Result();
        return *v8::String::Utf8Value(isolate, result);
    }

    static v8::Local<v8::String> to_v8_string(v8::Isolate* isolate,
                                              const std::string& str) {
        return v8::String::NewFromUtf8(isolate, str.c_str(),
                                       v8::NewStringType::kNormal)
            .ToLocalChecked();
    }

    static void throw_runtime_error(v8::Isolate* isolate,
                                    v8::Local<v8::Value> exception) {
        v8::String::Utf8Value error(isolate, exception);
        throw std::runtime_error(*error ? *error : "unknown error");
    }

    /**
     * dispose the isolate
     * this is called when the unique_ptr of the isolate goes out of scope
     */
    static void dispose_isolate(v8::Isolate* isolate) { isolate->Dispose(); }
};

/**
 * expose the V8System class to python
 */
PYBIND11_MODULE(_core, m) {   // NOLINT(misc-use-anonymous-namespace)
    py::class_<V8System>(m, "V8System")
        .def(py::init<>())
        .def_static("compile_and_invoke_source",
                    &V8System::compile_and_invoke_source)
        .def("invoke_function", &V8System::invoke_function);
}
