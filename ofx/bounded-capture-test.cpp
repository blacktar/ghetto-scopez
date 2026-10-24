#include "BoundedCapture.hpp"
#include <cassert>
#include <chrono>
#include <cstring>
#include <iostream>
#include <thread>
#include <vector>
struct Frame {std::shared_ptr<tap::CaptureBudget::Permit> permit;uint32_t seq;std::vector<uint32_t> bits;};
int main(){
 tap::CaptureBudget budget(3);tap::LatestMailbox<Frame> mailbox;
 const std::vector<uint32_t> bits{0x80000000,0x7fc12345,0x00000001,0x3f800001};
 auto frame=[&](uint32_t seq){auto p=budget.tryAcquire();if(!p)return std::shared_ptr<Frame>{};return std::make_shared<Frame>(Frame{std::move(p),seq,bits});};
 auto active=frame(0);assert(mailbox.tryPut(active));active=mailbox.take();
 assert(mailbox.tryPut(frame(1)));auto gpu=frame(2);assert(budget.used()==3);
 auto start=std::chrono::steady_clock::now();for(int i=0;i<100000;i++)assert(!frame(3));
 auto saturatedMs=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
 // A blocked consumer does not block admission checks; only 3 frames exist.
 assert(budget.used()==3);assert(mailbox.tryPut(std::move(gpu)));assert(budget.used()==2);
 auto newest=mailbox.take();assert(newest->seq==2&&newest->bits==bits);newest.reset();active.reset();assert(budget.used()==0);
 // Concurrent producers cannot overrun the shared budget. CPU bits are untouched.
 std::atomic<unsigned> peak{0},acquired{0};std::vector<std::thread> threads;
 for(int t=0;t<8;t++)threads.emplace_back([&]{for(int i=0;i<20000;i++){auto p=budget.tryAcquire();if(!p)continue;acquired++;auto n=budget.used();assert(n<=3);auto old=peak.load();while(n>old&&!peak.compare_exchange_weak(old,n)){}std::this_thread::yield();}});
 for(auto&t:threads)t.join();assert(budget.used()==0&&acquired>0);
 assert(mailbox.tryPut(frame(4)));mailbox.close();assert(budget.used()==0);assert(!mailbox.take());assert(!mailbox.tryPut(frame(5)));assert(budget.used()==0);
 // A pending item is latest-only even under sustained producer load.
 tap::LatestMailbox<Frame> latest;for(uint32_t seq=0;seq<10000;seq++)assert(latest.tryPut(frame(seq)));auto last=latest.take();assert(last->seq==9999&&last->bits==bits);last.reset();latest.close();assert(budget.used()==0);
 std::cout<<"PASS: 3-frame lifetime bound, 100000 nonwaiting saturation skips ("<<saturatedMs<<" ms), 8 concurrent producers (peak "<<peak<<"), latest-only delivery, exact payload bits, shutdown releases\n";
}
