#pragma once
#include <string>
namespace tap {
// Keep existing saved-project choice indices stable; append working-space mode.
inline bool uses709Basis(int choice){return choice!=2;}
inline std::string signalMetadata(int choice){
 const bool working=choice==3,bt709=uses709Basis(choice);
 return std::string("{\"model\":\"RGB\",\"range\":\"full\",\"matrix\":\"")+(bt709?"bt709":"bt2020-ncl")+
 "\",\"primaries\":\""+(working?"unknown":bt709?"bt709":"bt2020")+
 "\",\"transfer\":\"unknown\",\"domain\":\""+(working?"working":"encoded")+
 "\",\"codeBits\":10,\"measurementStage\":\"Resolve GTap node INPUT; "+
 (working?"raw working-space RGB, no colour transform; BT.709 analysis basis only":"user-declared encoded RGB, downstream transforms excluded")+"\"}";
}
}
