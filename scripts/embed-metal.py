from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'ofx/MetalAnalysis.metal').read_text()
(root/'ofx/MetalAnalysisSource.hpp').write_text('static const char* analysisSource=R"METAL('+source+')METAL";\n')
