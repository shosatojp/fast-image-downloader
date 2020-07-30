# dlimg

## Usage

```sh
python3 dlimg.py https://example.com/photos?query=dog
python3 dlimg.py --site example --query dog
```

## Developing

* create a python source file under `lib/sites/` and define these three objects.

```py
site = 'site name'
match = re.compile('https?://example.com/photos?query=.*')

async def info_getter(**args):
    ...
    return {
        'title': title,
        'imgs': imgs_generator # generate image urls
    }
```
