from .. import lib

site = 'anysite'
query = False

async def info_getter(**args):
    doc = await lib.fetch_doc(args['url'], **args)
    title = doc.select_one('title').text
    imgs_generator = lib.single_selector_collector(
        args['url'],
        'img',
        'src',
        **args
    )()
    return {
        'title': title,
        'imgs': imgs_generator
    }
