# tinyfaas

a tiny (<1k loc) faas platform. inspired by CloudFlare Workers/Vercel Edge
Functions. adventures in embedded V8.

try it out here:
https://tinyfaas.jchap.me/docs#/default/invoke_source_invoke_post

## overview

this is an educational project aimed at better understanding V8 and serverless
compute. also checked another box for me that i've been interested in which is
doing a python project with a native extension

## architecture

### server

-   FastAPI API
-   embedded V8 runtime
-   uses `scikit-build-core` and `pybind11` for c++ <> python bridge
-   SQLite for storing function/deployment data and source code
-   a "function" is an ESM module with a default export that is invoked as the
    function handler
-   functions are invoked in V8 isolates
-   isolates are kept warm and reused for subsequent invocations of the same
    functions (ie lambda cold/warm starts)
-   warm isolates are kept in an lru cache (128 of them) - arbitrary and simple
-   invocations will always hit the latest deployment of a function (even with a
    warm function running - it'll get evicted)

## cli

```sh
# invoke a script on the fly
echo 'export default async ()=>({hello:"world"})' | uv run cli invoke

# deploy a function and invoke it
uv run cli functions create --name "hello-world" # returns a function id
uv run cli functions deploy ./examples/basic.js --function-id fn-12345 # function id from above
uv run cli functions invoke --function-id fn-12345 --payload '{"name": "world"}'
```

## running

## notes

-   getting cmake working with vscode was funky - uv setup/ `uv run` worked out
    of the box, needed to tweak cmakelists a bit for vscode to pick up pybind11
-   i've only written a little c++ professionally, and no rust professionally,
    but have worked on i think what qualifies as a non-trivial project in rust
    (implementing a programming language), and c++ scares me - it fails in such
    funky, unhelpful ways. i'm sure there's tooling to help protect you from the
    footguns, but i don't know what it is. segfaults with no error messages,
    super unhelpful error messages, stuff like that. rust on the other hand is
    harder to get it to compile, but once it compiles you can be pretty sure
    it's gonna fail exactly where and how you think its gonna fail and be loud
    and obvious about it.
-   was an adventure getting v8 built for linux (docker) and getting cmake
    configured to build on both platforms. homebrew packages an older build of
    v8 that is NOT the one that ships with `libnode-dev` which was the easiest
    way to install on linux, and tinyfaas wouldn't compile on the latter due to
    some breaking api changes between the 2 versions. i ended up building from
    source off a release branch for both platforms. side note - building v8 was
    the first time i'd heard my fan turn on on my m4 pro. also kept running into
    "cannot allocate memory" from docker - realize i had a resource limit set,
    removed that and it worked but was slow. this was when building for amd64 as
    a result of
    [this](https://github.com/docker/roadmap/issues/384#issuecomment-1938832154).

## todo

-   [ ] ship cli to pypi
-   [ ] log from functions
-   [x] blow up if homebrew v8 version not docker version
-   [x] sqlite docker
-   [x] check how promises (dont) work
-   [x] docker
-   [x] invoke from stdin
-   [x] resource limits
-   [x] exception handling
-   [x] json to and from invocations
-   [x] cache compiled module
-   [x] store deployments
-   [x] logging

## resources

-   https://chromium.googlesource.com/v8/v8.git/+/4.5.103.9/test/cctest/test-serialize.cc#661
-   https://v8.dev/blog/custom-startup-snapshots
-   https://v8.dev/blog/code-caching
-   https://chromium.googlesource.com/v8/v8/+/branch-heads/11.9/samples/hello-world.cc
-   https://blog.cloudflare.com/cloud-computing-without-containers/
-   https://johnfoster.pge.utexas.edu/blog/posts/debugging-cc%2B%2B-libraries-called-by-python/
-   https://stackoverflow.com/questions/61490100/debugging-pybind11-extension-with-visual-studio-code-macos
-   https://github.com/cloudflare/workerd/blob/00d8c87890edb836bfd1445157f2a3960eb5bc5e/src/workerd/jsg/setup.c%2B%2B#L155
-   https://chromium.googlesource.com/v8/v8/+/branch-heads/11.9/samples/hello-world.cc
-   https://gist.github.com/surusek/4c05e4dcac6b82d18a1a28e6742fc23e?permalink_comment_id=4472429
-   https://github.com/nodejs/node-v0.x-archive/blob/master/lib/console.js
-   https://github.com/rogchap/v8go/issues/308
-   https://v8.github.io/api/head/classv8_1_1ResourceConstraints.html

<img src="https://v8.dev/_img/docs/embed/local-persist-handles-review.png" />
