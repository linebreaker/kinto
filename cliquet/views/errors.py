from functools import wraps

from pyramid import httpexceptions
from pyramid.security import forget, NO_PERMISSION_REQUIRED
from pyramid.view import (
    forbidden_view_config, notfound_view_config, view_config
)

from cliquet import logger
from cliquet.errors import format_error, ERRORS, HTTPInternalServerError
from cliquet.utils import reapply_cors


def cors(view):
    """Decorator to make sure CORS headers are correctly processed."""

    @wraps(view)
    def wrap_view(request, *args, **kwargs):
        response = view(request, *args, **kwargs)

        # We need to re-apply the CORS checks done by Cornice, since we're
        # recreating the response from scratch.
        return reapply_cors(request, response)

    return wrap_view


@forbidden_view_config()
@cors
def authorization_required(request):
    """Distinguish authentication required (``401 Unauthorized``) from
    not allowed (``403 Forbidden``).
    """
    if not request.authenticated_userid:
        response = httpexceptions.HTTPUnauthorized(
            body=format_error(
                401, ERRORS.MISSING_AUTH_TOKEN, "Unauthorized",
                "Please authenticate yourself to use this endpoint."),
            content_type='application/json')
        response.headers.extend(forget(request))
        return response

    response = httpexceptions.HTTPForbidden(
        body=format_error(
            403, ERRORS.FORBIDDEN, "Forbidden",
            "This user cannot access this resource."),
        content_type='application/json')
    return response


@notfound_view_config()
@cors
def page_not_found(request):
    """Return a JSON 404 error page."""
    response = httpexceptions.HTTPNotFound(
        body=format_error(
            404, ERRORS.MISSING_RESOURCE, "Not Found",
            "The resource your are looking for could not be found."),
        content_type='application/json')
    return response


@view_config(context=Exception, permission=NO_PERMISSION_REQUIRED)
def error(context, request):
    """Catch server errors and trace them."""
    if isinstance(context, httpexceptions.Response):
        return reapply_cors(request, context)

    logger.exception(context)

    response = HTTPInternalServerError()

    return reapply_cors(request, response)