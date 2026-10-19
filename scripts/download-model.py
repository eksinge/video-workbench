"""Explicitly download a selected ASR model; no audio is uploaded."""
from pathlib import Path
import argparse
from huggingface_hub import snapshot_download
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',required=True);p.add_argument('--out',required=True);p.add_argument('--revision',default='main');a=p.parse_args()
    target=Path(a.out).resolve();target.mkdir(parents=True,exist_ok=True)
    snapshot_download(repo_id=a.repo,revision=a.revision,local_dir=str(target),allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.*','preprocessor_config.json'])
    print('Model ready at',target)
