from docutils import nodes


def bug_role(name, rawtext, text, lineno, inliner, *args, **kwargs):
    app = inliner.document.settings.env.app
    url_tmpl = app.config.bug_url_template or "missing/%s"
    node = nodes.reference(
        rawtext,
        "[%s]" % text,
        refuri=url_tmpl % text)
    return [node], []


def setup(app):
    app.add_role('bug', bug_role)
    app.add_config_value('bug_url_template', None, 'env')
