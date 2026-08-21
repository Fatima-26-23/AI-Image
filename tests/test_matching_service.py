"""
Definition of Done: "Semantic matching works for equivalent concepts."
cosine_similarity is the core primitive the whole ranking step depends on --
if this is wrong, everything built on top of it is wrong too. These tests
pin down its behavior with known vectors before trusting it on real
embeddings.
"""

import math

import pytest

from app.services.matching_service import cosine_similarity


def test_identical_vectors_similarity_one():
    v = [0.5, 0.5, 0.5, 0.5]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_orthogonal_vectors_similarity_zero():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_opposite_vectors_similarity_negative_one():
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)


def test_scaling_does_not_change_similarity():
    """Cosine similarity is magnitude-invariant -- a caption embedded twice
    with slightly different norms should still compare consistently."""
    a = [1, 2, 3]
    b = [2, 4, 6]  # same direction, different magnitude
    assert cosine_similarity(a, b) == pytest.approx(1.0)


def test_zero_vector_returns_zero_not_crash():
    """A zero embedding (e.g. embedding call returned garbage) must degrade
    safely to 0 similarity, never a ZeroDivisionError reaching the guard."""
    assert cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0


def test_dimension_mismatch_raises():
    """Comparing embeddings from two different providers/models (different
    dimensionality) must fail loudly, not silently produce a bogus score."""
    with pytest.raises(ValueError):
        cosine_similarity([1, 2, 3], [1, 2])


def test_similar_direction_scores_higher_than_dissimilar():
    """Simulates the real scenario: a 'fox' caption embedding should score
    closer to a 'fox' post embedding than an unrelated 'kitchen' embedding
    does, even with made-up low-dimensional vectors standing in for real
    ones -- this is what top-1 precision measures on real data."""
    post_fox = [0.9, 0.1, 0.0]
    image_fox = [0.85, 0.15, 0.05]
    image_kitchen = [0.0, 0.1, 0.95]

    fox_score = cosine_similarity(post_fox, image_fox)
    kitchen_score = cosine_similarity(post_fox, image_kitchen)

    assert fox_score > kitchen_score
