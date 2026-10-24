#pragma once
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <memory>
#include <mutex>

namespace tap {
// A permit follows a snapshot from GPU submission until its last owner releases
// it (including readback callbacks, pending delivery and active network writes).
class CaptureBudget {
 struct State {std::atomic<unsigned> used{0};const unsigned limit;explicit State(unsigned n):limit(n){}};
 std::shared_ptr<State> state;
public:
 struct Permit {std::shared_ptr<State> state;explicit Permit(std::shared_ptr<State> s):state(std::move(s)){}~Permit(){state->used.fetch_sub(1);}};
 explicit CaptureBudget(unsigned limit=3):state(std::make_shared<State>(limit)){}
 std::shared_ptr<Permit> tryAcquire(){auto n=state->used.load();while(n<state->limit){if(state->used.compare_exchange_weak(n,n+1)){try{return std::make_shared<Permit>(state);}catch(...){state->used.fetch_sub(1);throw;}}}return {};}
 unsigned used()const{return state->used.load();}
};
// Producers never wait for the consumer mutex or the network. The one pending
// item is replaced, not appended; destruction of replaced data is outside lock.
template<class T> class LatestMailbox {
 std::mutex mutex;std::condition_variable wake;std::shared_ptr<T> pending;bool closed=false;
public:
 bool tryPut(std::shared_ptr<T> value){std::unique_lock<std::mutex>lock(mutex,std::try_to_lock);if(!lock.owns_lock()||closed)return false;pending.swap(value);lock.unlock();wake.notify_one();return true;}
 std::shared_ptr<T> take(){std::unique_lock<std::mutex>lock(mutex);wake.wait(lock,[&]{return closed||bool(pending);});if(closed)return {};return std::move(pending);}
 std::shared_ptr<T> takeFor(std::chrono::milliseconds timeout){std::unique_lock<std::mutex>lock(mutex);wake.wait_for(lock,timeout,[&]{return closed||bool(pending);});if(closed)return {};return std::move(pending);}
 void close(){std::shared_ptr<T> discarded;{std::lock_guard<std::mutex>lock(mutex);closed=true;discarded=std::move(pending);}wake.notify_all();}
};
}
