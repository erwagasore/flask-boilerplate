from flask import jsonify


def bad_request(e):
    response = jsonify({
        'status': 400,
        'error': 'bad request',
        'message': 'malformed request'
    })
    response.status_code = 400
    return response


def unauthorized():
    response = jsonify(
        {
            'status': 401,
            'error': 'unauthorized',
            'message': 'unauthorized access'
        }
    )
    response.status_code = 401
    return response


def forbidden(e):
    response = jsonify({
        'status': 403,
        'error': 'forbidden',
        'message': 'forbidden access'
    })
    response.status_code = 403
    return response


def not_found(e):
    response = jsonify({
        'status': 404,
        'error': 'not found',
        'message': 'invalid resource URI'
    })
    response.status_code = 404
    return response


def method_not_supported(e):
    response = jsonify({
        'status': 405,
        'error': 'method not supported',
        'message': 'method is not supported'
    })
    response.status_code = 405
    return response


def conflict(e):
    return e.to_result()
