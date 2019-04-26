import functools
from flask import url_for, request

from app.factory import APIResult


def paginate(collection, version=None, max_per_page=25):
    """Converts a database query into a collection containing pages and its details"""
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # invoke the wrapped function
            extra = {}
            query = f(*args, **kwargs)

            # check if it a collection
            if isinstance(query, tuple):
                query, extra = query

            # get ordering arguments
            order = request.args.get('order_by', 'created_at', type=str)
            query = query.order_by(order)
            # query = sort_query(query, order)

            # obtain pagination arguments from the URL's query string
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', max_per_page, type=int), max_per_page)
            expanded = 1 if request.args.get('expanded', 0, type=int) != 0 else None

            # run the query with Flask-SQLAlchemy's pagination
            p = query.paginate(page, per_page)

            # build the pagination metadata to include in the response
            pages = {'page': page, 'per_page': per_page, 'total': p.total, 'pages': p.pages}

            if p.has_prev:
                pages['prev_url'] = url_for(
                    request.endpoint, page=p.prev_num, per_page=per_page,
                    expanded=expanded, _external=True, **kwargs)
            else:
                pages['prev_url'] = None

            if p.has_next:
                pages['next_url'] = url_for(
                    request.endpoint, page=p.next_num, per_page=per_page,
                    expanded=expanded, _external=True, **kwargs)
            else:
                pages['next_url'] = None

            pages['first_url'] = url_for(request.endpoint, page=1, per_page=per_page,
                                         expanded=expanded, _external=True, **kwargs)
            pages['last_url'] = url_for(request.endpoint, page=p.pages, per_page=per_page,
                                        expanded=expanded, _external=True, **kwargs)

            results = [
                _.export_data(request=request, **extra) for _ in p.items] if expanded else [
                    _.get_url(request=request, **extra) for _ in p.items]

            return APIResult({collection: results, 'pages': pages})
        return wrapped
    return decorator
