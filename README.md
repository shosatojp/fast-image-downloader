# dlimg

## Install

```sh
pip3 install dlimg
```

## Usage

```sh
dlimg 'https://wear.jp/coordinate/'
dlimg --site google --query dog
```

## Available Sites

| site                 | query |
| -------------------- | ----- |
| google               |   O   |
| bing                 |   O   |
| unsplash             |   O   |
| anysite              |   X   |
| irasutoya            |   O   |
| wear                 |   X   |

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
