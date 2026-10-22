"""Download from the publisher's public Kaggle endpoint and keep events only."""
from pathlib import Path
import gzip, shutil, urllib.request, zipfile

ROOT=Path(__file__).resolve().parents[1]
URL='https://www.kaggle.com/api/v1/datasets/download/retailrocket/ecommerce-dataset'

if __name__=='__main__':
    data=ROOT/'data'; data.mkdir(exist_ok=True)
    destination=data/'events.csv.gz'
    if destination.exists():
        print(f'Already present: {destination}')
    else:
        archive=data/'retailrocket.zip'
        urllib.request.urlretrieve(URL,archive)
        with zipfile.ZipFile(archive) as z, z.open('events.csv') as source, gzip.open(destination,'wb') as out:
            shutil.copyfileobj(source,out)
        archive.unlink()
        print(destination)
