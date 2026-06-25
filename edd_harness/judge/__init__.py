"""Judge backends — pluggable, flat-cost by construction.

The metered API-key backend is never returned by the factory; it is reachable only by a
consumer explicitly constructing it. See ``factory.resolve_backend``.
"""
