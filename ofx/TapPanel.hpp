#pragma once
#include <sstream>
#include <string>
#include <vector>
namespace tap {
struct PanelInfo {std::string host="Unavailable",snapshot="Not refreshed";std::vector<std::string> urls,viewers;};
inline PanelInfo parsePanelInfo(const std::string&text){PanelInfo out;std::istringstream stream(text);std::string line;for(;std::getline(stream,line);){if(line.rfind("Scopes host: ",0)==0)out.host=line.substr(13);else if(line.rfind("http://",0)==0||line.rfind("https://",0)==0)out.urls.push_back(line);else if(line.rfind("Local address: ",0)==0)out.urls.push_back(line.substr(15));else if(line.rfind("Snapshot: ",0)==0)out.snapshot=line.substr(10);else if(line.find(": listening (")!=std::string::npos||line.find(": connected, stopped")!=std::string::npos)out.viewers.push_back(line);}return out;}
void showPanelAbout();
void copyPanelText(const std::string&text);
}
