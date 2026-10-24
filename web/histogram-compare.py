"""Independent histogram counts + lossless GPU rendering comparison."""
from visual_reference import *
out=Path(sys.argv[1]);results=[];negative={};(out/'sources').mkdir(exist_ok=True)
for case in json.loads((out/'manifest.json').read_text()):
 c=case['plots'][0]['rendered']['config'];rgb=source(case['fixture'],c);hist=planes(rgb,c)[2];n=rgb.shape[0]*rgb.shape[1]
 path=out/'sources'/(case['fixture']+'.tiff');tifffile.imwrite(path,rgb.astype(np.float32),photometric='rgb',compression='deflate');assert np.array_equal(tifffile.imread(path).view(np.uint32),rgb.astype(np.float32).view(np.uint32))
 assert case['option']=='RGB histogram · Separate';assert all(p['rendered']['config']['activeScopes']==[2] for p in case['plots']);assert case['plots'][0]['axes']==case['plots'][1]['axes']
 for scope,mode in [(2,2),(8,5)]:
  actual=np.array(Image.open(out/f"{case['fixture']}-{scope}-lossless.png").convert('RGB'));h,w=actual.shape[:2]
  expected,bg=reference(mode,hist,w,h,n);high,_=reference(mode,hist,w,h,n,depth=16);tifffile.imwrite(out/f"{case['fixture']}-{scope}-expected.tiff",high,photometric='rgb',compression='deflate')
  Image.fromarray(expected).save(out/f"{case['fixture']}-{scope}-expected.png");r,diff=compare(actual,expected,bg,tolerance=2);results.append({'fixture':case['fixture'],'scope':scope,**r})
  if case['fixture']=='tonal-casts' and scope==8:
   wrong,_=reference(5,hist[::-1],w,h,n);negative['swapped_red_blue_rejected']=not compare(wrong,expected,bg,tolerance=2)[0]['pass']
   negative['overlay_instead_of_separate_rejected']=not compare(reference(2,hist,w,h,n)[0],expected,bg,tolerance=2)[0]['pass']
result={'comparisons':results,'negative_controls':negative,'pass':all(r['pass'] for r in results) and all(negative.values())};(out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(0 if result['pass'] else 1)
