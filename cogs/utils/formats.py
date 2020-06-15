# -*- coding: utf-8 -*-

from traceback import format_exception


def format_exec(exc):
    return "".join(format_exception(type(exc), exc, exc.__traceback__))


def format_error(error, *, strip=False):
    formatted = "".join(format_exception(type(error), error, error.__traceback__, limit=1))
    if strip:
        formatted = formatted.splitlines()
        formatted.pop(1)
        formatted.pop(1)
        return "\n".join(formatted)
    return formatted


def human_join(seq, delimiter=', ', final='and'):
    if isinstance(seq, str):
        return seq
    size = len(seq)
    if size == 0:
        return ''

    if size == 1:
        return seq[0]

    if size == 2:
        return f'{seq[0]} {final} {seq[1]}'

    return f'{delimiter.join(seq[:-1])} {final} {seq[-1]}'
