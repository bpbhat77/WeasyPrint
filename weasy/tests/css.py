# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
from attest import Tests, assert_hook
from lxml import html
#from lxml.html import html5parser as html  # API is the same as lxml.html
import cssutils
from cssutils.helper import path2url

from .. import css
from ..css.computed_values import get_value

from . import resource_filename


suite = Tests()

def parse_html(filename):
    """Parse an HTML file from the test resources and resolve relative URL."""
    document = html.parse(path2url(resource_filename(filename))).getroot()
    document.make_links_absolute()
    return document


@suite.test
def test_find_stylesheets():
    document = parse_html('doc1.html')
    
    sheets = list(css.find_stylesheets(document))
    assert len(sheets) == 2
    # Also test that stylesheets are in tree order
    assert [s.href.rsplit('/', 1)[-1] for s in sheets] \
        == ['sheet1.css', 'doc1.html']

    rules = list(rule for sheet in sheets
                      for rule in css.resolve_import_media(sheet, 'print'))
    assert len(rules) == 8
    # Also test appearance order
    assert [rule.selectorText for rule in rules] \
        == ['li', 'p', 'ul', 'a', 'a:after', ':first', 'ul', 
            'body > h1:first-child']


@suite.test
def test_expand_shorthands():
    sheet = cssutils.parseFile(resource_filename('sheet2.css'))
    assert sheet.cssRules[0].selectorText == 'li'
    style = sheet.cssRules[0].style
    assert style['margin'] == '2em 0'
    assert style['margin-bottom'] == '3em'
    assert style['margin-left'] == '4em'
    assert not style['margin-top']
    css.expand_shorthands(sheet)
    # expand_shorthands() builds new style object
    style = sheet.cssRules[0].style
    assert not style['margin']
    assert style['margin-top'] == '2em'
    assert style['margin-right'] == '0'
    assert style['margin-bottom'] == '2em', \
        "3em was before the shorthand, should be masked"
    assert style['margin-left'] == '4em', \
        "4em was after the shorthand, should not be masked"


@suite.test
def test_annotate_document():
    user_stylesheet = cssutils.parseFile(resource_filename('user.css'))
    ua_stylesheet = cssutils.parseFile(resource_filename('mini_ua.css'))
    document = parse_html('doc1.html')
    
    css.annotate_document(document, [user_stylesheet], [ua_stylesheet])
    
    # Element objects behave a lists of their children
    head, body = document
    h1, p, ul = body
    li = list(ul)
    a, = li[0]
    after = a.pseudo_elements['after']
    
    assert h1.style['background-image'][0].uri == 'file://' \
        + os.path.abspath(resource_filename('logo_small.png'))
    
    assert h1.style['font-weight'][0].value == 700
    
    sides = ('-top', '-right', '-bottom', '-left')
    # 32px = 1em * font-size: 2em * initial 16px
    for side, expected_value in zip(sides, ('32px', '0', '32px', '0')):
        assert get_value(p.style, 'margin' + side) == expected_value
    
    # 32px = 2em * initial 16px
    for side, expected_value in zip(sides, ('32px', '32px', '32px', '32px')):
        assert get_value(ul.style, 'margin' + side) == expected_value
    
    # thick = 5px, 0.25 inches = 96*.25 = 24px
    for side, expected_value in zip(sides, ('0', '5px', '0', '24px')):
        assert get_value(ul.style, 'border' + side + '-width') == expected_value
    
    # 32px = 2em * initial 16px
    # 64px = 4em * initial 16px
    for side, expected_value in zip(sides, ('32px', '0', '32px', '64px')):
        assert get_value(li[0].style, 'margin' + side) == expected_value
    
    assert get_value(a.style, 'text-decoration') == 'underline'
    
    color = a.style['color'][0]
    assert (color.red, color.green, color.blue, color.alpha) == (255, 0, 0, 1)

    assert [v.value for v in after.style['content']] \
        == [' [', 'attr(href)', ']']

    # TODO much more tests here: test that origin and selector precedence
    # and inheritance are correct, ...
