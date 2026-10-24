#include "TapInfo.hpp"
#include <iostream>
int main(int argc,char**argv){std::cout<<tap::fetchHostInfo(argc>1?std::stoi(argv[1]):8765)<<std::endl;}
