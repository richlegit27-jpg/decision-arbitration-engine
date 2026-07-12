from flask import jsonify

from nova_backend.services.compute_backend_readiness import (
    build_backend_readiness,
)


def get_backend_readiness():
    return jsonify(
        build_backend_readiness()
    )
