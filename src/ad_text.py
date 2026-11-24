"""Preserve paragraph and list boundaries for requirement interpretation."""
import html
import re
from html.parser import HTMLParser


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.hidden=0

    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:
            self.hidden+=1
        if tag in {'p','div','li','br','h1','h2','h3','h4','ul','ol','strong','b'}:
            self.parts.append('\n')

    def handle_endtag(self,tag):
        if tag in {'script','style'}:
            self.hidden=max(0,self.hidden-1)
        if tag in {'p','div','li','h1','h2','h3','h4','ul','ol','strong','b'}:
            self.parts.append('\n')

    def handle_data(self,data):
        if not self.hidden:
            self.parts.append(data)


def structured_text(raw):
    text=html.unescape(raw or '')
    if re.search(r'</?(?:p|div|li|br|h[1-6]|strong|ul|ol)\b',text,re.I):
        parser=_Text(); parser.feed(text); text=''.join(parser.parts)
    lines=[re.sub(r'[^\S\n]+',' ',line).strip() for line in text.replace('\r\n','\n').split('\n')]
    return re.sub(r'\n{3,}','\n\n','\n'.join(lines)).strip()
