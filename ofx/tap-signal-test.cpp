#include "TapSignal.hpp"
#include <cassert>
#include <iostream>
int main(){
 assert(tap::uses709Basis(1));assert(!tap::uses709Basis(2));assert(tap::uses709Basis(3));
 for(int choice:{1,2,3})std::cout<<tap::signalMetadata(choice)<<"\n";
}
