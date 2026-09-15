"""Geometry repair helpers for converted MDX models."""

from __future__ import annotations

import math
from dataclasses import dataclass


EPSILON = 1e-8


@dataclass
class RepairStats:
    geosets: int = 0
    normals_rebuilt: int = 0
    tangents_built: int = 0
    pivots_added: int = 0


def _vector_length(vec):
    return math.sqrt((vec[0] * vec[0]) + (vec[1] * vec[1]) + (vec[2] * vec[2]))


def _normalize(vec, fallback=None):
    length = _vector_length(vec)
    if length <= EPSILON:
        return fallback[:] if fallback is not None else [0.0, 0.0, 1.0]
    inv = 1.0 / length
    return [vec[0] * inv, vec[1] * inv, vec[2] * inv]


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _dot(a, b):
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def _cross(a, b):
    return [
        (a[1] * b[2]) - (a[2] * b[1]),
        (a[2] * b[0]) - (a[0] * b[2]),
        (a[0] * b[1]) - (a[1] * b[0]),
    ]


def _build_fallback_tangent(normal):
    axis = [0.0, 0.0, 1.0] if abs(normal[2]) < 0.99 else [0.0, 1.0, 0.0]
    tangent = _normalize(_cross(axis, normal), fallback=[1.0, 0.0, 0.0])
    return tangent + [1.0]


def _get_vertex(vertices, index):
    base = index * 3
    return [float(vertices[base]), float(vertices[base + 1]), float(vertices[base + 2])]


def _set_vertex(values, index, vec):
    base = index * 3
    values[base] = vec[0]
    values[base + 1] = vec[1]
    values[base + 2] = vec[2]


def _clone_extent(extent_cls, bounds_radius, minimum, maximum):
    extent = extent_cls()
    extent.bounds_radius = bounds_radius
    extent.min = list(minimum)
    extent.max = list(maximum)
    return extent


def count_id_objects(model) -> int:
    names = (
        "bones",
        "lights",
        "helpers",
        "attachments",
        "particle_emitters",
        "particle_emitters2",
        "particle_emitters_popcorn",
        "ribbon_emitters",
        "event_objects",
        "collision_shapes",
    )
    return sum(len(getattr(model, name, [])) for name in names)


def repair_pivot_points(model) -> int:
    missing = count_id_objects(model) - len(getattr(model, "pivot_points", []))
    if missing <= 0:
        return 0
    model.pivot_points.extend([[0.0, 0.0, 0.0] for _ in range(missing)])
    return missing


def calculate_geoset_extent(geoset):
    if not geoset.vertices:
        return 0.0, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    max_radius = 0.0

    for i in range(len(geoset.vertices) // 3):
        x, y, z = _get_vertex(geoset.vertices, i)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        min_z = min(min_z, z)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        max_z = max(max_z, z)
        max_radius = max(max_radius, math.sqrt((x * x) + (y * y) + (z * z)))

    return max_radius, [min_x, min_y, min_z], [max_x, max_y, max_z]


def recalculate_normals(geoset) -> int:
    vertex_count = len(geoset.vertices) // 3
    if vertex_count == 0 or not geoset.faces:
        if geoset.normals is None or len(geoset.normals) != len(geoset.vertices):
            geoset.normals = [0.0] * len(geoset.vertices)
        return 0

    position_groups = {}
    face_normals_by_vertex = [[] for _ in range(vertex_count)]

    for i in range(vertex_count):
        position_groups.setdefault(tuple(_get_vertex(geoset.vertices, i)), []).append(i)

    for face_index in range(0, len(geoset.faces), 3):
        if face_index + 2 >= len(geoset.faces):
            break
        ia = int(geoset.faces[face_index])
        ib = int(geoset.faces[face_index + 1])
        ic = int(geoset.faces[face_index + 2])
        if ia >= vertex_count or ib >= vertex_count or ic >= vertex_count:
            continue
        a = _get_vertex(geoset.vertices, ia)
        b = _get_vertex(geoset.vertices, ib)
        c = _get_vertex(geoset.vertices, ic)
        face_normal = _normalize(_cross(_sub(b, a), _sub(c, b)), fallback=None)
        if _vector_length(face_normal) <= EPSILON:
            continue
        face_normals_by_vertex[ia].append(face_normal)
        face_normals_by_vertex[ib].append(face_normal)
        face_normals_by_vertex[ic].append(face_normal)

    geoset.normals = [0.0] * len(geoset.vertices)
    rebuilt = 0
    for vertex_indices in position_groups.values():
        normal_sum = [0.0, 0.0, 0.0]
        for vertex_index in vertex_indices:
            for face_normal in face_normals_by_vertex[vertex_index]:
                normal_sum[0] += face_normal[0]
                normal_sum[1] += face_normal[1]
                normal_sum[2] += face_normal[2]
        normalized = _normalize(normal_sum, fallback=[0.0, 0.0, 1.0])
        for vertex_index in vertex_indices:
            _set_vertex(geoset.normals, vertex_index, normalized)
            rebuilt += 1
    return rebuilt


def recalculate_tangents(geoset) -> int:
    vertex_count = len(geoset.vertices) // 3
    if vertex_count == 0:
        geoset.tangents = []
        return 0
    if not geoset.normals or len(geoset.normals) != len(geoset.vertices):
        recalculate_normals(geoset)
    if not geoset.uv_sets:
        geoset.tangents = []
        for vertex_index in range(vertex_count):
            normal = _normalize(_get_vertex(geoset.normals, vertex_index))
            geoset.tangents.extend(_build_fallback_tangent(normal))
        return vertex_count

    uv_set = geoset.uv_sets[0]
    tan1 = [[0.0, 0.0, 0.0] for _ in range(vertex_count)]
    tan2 = [[0.0, 0.0, 0.0] for _ in range(vertex_count)]

    for face_index in range(0, len(geoset.faces), 3):
        if face_index + 2 >= len(geoset.faces):
            break
        ia = int(geoset.faces[face_index])
        ib = int(geoset.faces[face_index + 1])
        ic = int(geoset.faces[face_index + 2])
        if ia >= vertex_count or ib >= vertex_count or ic >= vertex_count:
            continue

        p1 = _get_vertex(geoset.vertices, ia)
        p2 = _get_vertex(geoset.vertices, ib)
        p3 = _get_vertex(geoset.vertices, ic)
        uv1 = [float(uv_set[ia * 2]), float(uv_set[(ia * 2) + 1])]
        uv2 = [float(uv_set[ib * 2]), float(uv_set[(ib * 2) + 1])]
        uv3 = [float(uv_set[ic * 2]), float(uv_set[(ic * 2) + 1])]

        x1, y1, z1 = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
        x2, y2, z2 = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
        s1, t1 = uv2[0] - uv1[0], uv2[1] - uv1[1]
        s2, t2 = uv3[0] - uv1[0], uv3[1] - uv1[1]
        denominator = (s1 * t2) - (s2 * t1)
        if abs(denominator) <= EPSILON:
            continue

        inv = 1.0 / denominator
        sdir = [((t2 * x1) - (t1 * x2)) * inv, ((t2 * y1) - (t1 * y2)) * inv, ((t2 * z1) - (t1 * z2)) * inv]
        tdir = [((s1 * x2) - (s2 * x1)) * inv, ((s1 * y2) - (s2 * y1)) * inv, ((s1 * z2) - (s2 * z1)) * inv]
        for vertex_index in (ia, ib, ic):
            tan1[vertex_index][0] += sdir[0]
            tan1[vertex_index][1] += sdir[1]
            tan1[vertex_index][2] += sdir[2]
            tan2[vertex_index][0] += tdir[0]
            tan2[vertex_index][1] += tdir[1]
            tan2[vertex_index][2] += tdir[2]

    tangents = []
    for vertex_index in range(vertex_count):
        normal = _normalize(_get_vertex(geoset.normals, vertex_index))
        tangent = tan1[vertex_index]
        tangent = [
            tangent[0] - (normal[0] * _dot(normal, tangent)),
            tangent[1] - (normal[1] * _dot(normal, tangent)),
            tangent[2] - (normal[2] * _dot(normal, tangent)),
        ]
        tangent = _normalize(tangent, fallback=None)
        if _vector_length(tangent) <= EPSILON:
            tangents.extend(_build_fallback_tangent(normal))
            continue
        handedness = -1.0 if _dot(_cross(normal, tangent), tan2[vertex_index]) < 0.0 else 1.0
        tangents.extend([tangent[0], tangent[1], tangent[2], handedness])

    geoset.tangents = tangents
    return vertex_count


def repair_model_geometry(model, recalc_normals_enabled: bool = True, recalc_tangents_enabled: bool = True) -> RepairStats:
    from PyMdlxConverter.parsers.mdlx.extent import Extent

    stats = RepairStats()
    geoset_extents = []
    stats.pivots_added += repair_pivot_points(model)

    for geoset in model.geosets:
        stats.geosets += 1
        if recalc_normals_enabled:
            stats.normals_rebuilt += recalculate_normals(geoset)
        bounds_radius, minimum, maximum = calculate_geoset_extent(geoset)
        geoset.extent = _clone_extent(Extent, bounds_radius, minimum, maximum)
        geoset_extents.append((bounds_radius, minimum, maximum))
        if recalc_tangents_enabled:
            stats.tangents_built += recalculate_tangents(geoset)

    if not geoset_extents:
        model.extent = _clone_extent(Extent, 0.0, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        return stats

    model_min = [min(e[1][axis] for e in geoset_extents) for axis in range(3)]
    model_max = [max(e[2][axis] for e in geoset_extents) for axis in range(3)]
    model_bounds_radius = max(e[0] for e in geoset_extents)
    model.extent = _clone_extent(Extent, model_bounds_radius, model_min, model_max)

    sequence_count = len(model.sequences)
    for geoset in model.geosets:
        geoset.sequence_extents = [_clone_extent(Extent, model_bounds_radius, model_min, model_max) for _ in range(sequence_count)]
    for sequence in model.sequences:
        sequence.extent = _clone_extent(Extent, model_bounds_radius, model_min, model_max)
    return stats
