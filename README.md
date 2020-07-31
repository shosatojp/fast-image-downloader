# dlimg

## Installation

```sh
pip3 install dlimg
```

## Usage

```sh
# download images in url
dlimg 'https://wear.jp/coordinate/'

# download 'dog' from google
dlimg --site google --query dog

# download images with one second for interval
dlimg --site bing --query cat --wait 1
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
