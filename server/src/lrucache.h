/**
 * LRU Cache
 * header-only implementation
 * https://www.reddit.com/r/cpp/comments/lorm3s/header_only_vs_hppcpp_styles/
 */

#include <iostream>
#include <list>
#include <unordered_map>

template <typename K, typename V>
class LRUCache {
   private:
    int capacity_;
    std::list<std::pair<K, V>> cache_;
    std::unordered_map<K, typename std::list<std::pair<K, V>>::iterator>
        lookup_;

   public:
    explicit LRUCache(int cap) : capacity_(cap) {}

    V get(K key) {
        auto it = lookup_.find(key);
        if (it == lookup_.end()) {
            return V{};   // Key not found
        }

        // Move the accessed element to the front
        cache_.splice(cache_.begin(), cache_, it->second);
        return it->second->second;
    }

    void put(K key, V value) {
        auto it = lookup_.find(key);
        if (it != lookup_.end()) {
            // Update value and move to front
            it->second->second = value;
            cache_.splice(cache_.begin(), cache_, it->second);
        } else {
            if (cache_.size() == capacity_) {
                // Remove least recently used element
                auto last = cache_.back();
                lookup_.erase(last.first);
                cache_.pop_back();
            }
            // Insert new element at front
            cache_.push_front({key, value});
            lookup_[key] = cache_.begin();
        }
    }
};
