# Lazy Vercel WSGI wrapper for the Flask app
# Exports both `handler` and `app` callables so the Vercel Python runtime
# can invoke the application. The real Flask app is created lazily on the
# first request to avoid import-time side-effects (DB connections, etc.).

_app = None

def _get_app():
    global _app
    if _app is None:
        # Import inside function to defer module-level imports until runtime
        from app import create_app

        _app = create_app()
    return _app


def _get_wsgi_app():
    return _get_app().wsgi_app


def handler(environ, start_response):
    """WSGI handler expected by some Vercel Python runtimes."""
    return _get_wsgi_app()(environ, start_response)


# Expose a top-level WSGI callable named `app` as well. This is compatible
# with runtimes that look for a top-level `app` variable.
app = handler
