# -*- coding: utf-8 -*-

from docutils import nodes


def bug_role(name, rawtext, text, lineno, inliner, *args, **kwargs):
    app = inliner.document.settings.env.app
    url_tmpl = app.config.bug_url_template or "missing/%s"
    node = nodes.reference(
        rawtext,
        "[%s]" % text,
        refuri=url_tmpl % text)
    return [node], []


def pr_role(name, rawtext, text, lineno, inliner, *args, **kwargs):
    app = inliner.document.settings.env.app
    if name == "pr":
        url_tmpl = app.config.pr_url_template
    else:
        url_tmpl = app.config.bbpr_url_template
    url_tmpl = url_tmpl or "missing/%s"
    node = nodes.reference(
        rawtext,
        "[%s-%s]" % (name, text),
        refuri=url_tmpl % text)
    return [node], []


def setup(app):
    app.add_role('bug', bug_role)
    app.add_config_value('bug_url_template', None, 'env')
    app.add_role('bb-pr', pr_role)
    app.add_role('pr', pr_role)
    app.add_config_value('pr_url_template', None, 'env')
    app.add_config_value('bbpr_url_template', None, 'env')
