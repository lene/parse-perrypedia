#!/usr/bin/env python3
__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

from argparse import ArgumentParser, Namespace
from pprint import pprint
from sys import argv

from parse_perrypedia.parse import PerryRhodanPage, count_authors
from parse_perrypedia.upload import Uploader


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Read Perrypedia and print info about Perry Rhodan issues")
    parser.add_argument('-s', '--start', default=1, type=int, help='First issue')
    parser.add_argument('-e', '--end', default=0, type=int, help='Last issue')
    parser.add_argument(
        '-g', '--goodreads', action='store_true', help='Print info required by goodreads'
    )
    parser.add_argument(
        '-u', '--upload', action='store_true',
        help='Upload novel descriptions to goodreads, if not present'
    )
    parser.add_argument('-a', '--goodreads-account', help='email used for goodreads account')
    parser.add_argument('-p', '--goodreads-password', help='password used for goodreads account')
    return parser.parse_args(argv[1:])


def run(opts: Namespace):
    if opts.upload and not (opts.goodreads_account and opts.goodreads_password):
        raise ValueError('when choosing upload, account and password must be given')
    pages = PerryRhodanPage.slice(opts.start, opts.end if opts.end else opts.start)
    if opts.goodreads:
        for page in pages:
            print(page.goodreads_data())
    else:
        print(len([page for page in pages if page.synopsis is not None]), 'with synopsis')

        authors = count_authors(pages)
        pprint(
            sorted([(a[0], a[1]) for a in authors.items()], key=lambda pair: pair[1], reverse=True))
    if opts.upload:
        Uploader(opts.goodreads_account, opts.goodreads_password).upload(pages)


def main():
    run(parse_args())


if __name__ == '__main__':
    main()
