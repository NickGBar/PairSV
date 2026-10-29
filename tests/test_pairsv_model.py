from __future__ import annotations

import pytest
torch = pytest.importorskip("torch", reason="PAIR-SV model smoke tests require the project PyTorch dependency")

from deepsv.models.pairsv import M4_ABLATION_VARIANTS, PAIRSV_VARIANTS, PairSV


@pytest.fixture
def inputs():
    torch.manual_seed(7)
    return {
        "images": torch.rand(2, 2, 6, 64, 128),
        "candidate_features": torch.rand(2, 32),
        "read_features": torch.rand(2, 24),
        "scalar_features": torch.rand(2, 17),
    }


@pytest.mark.parametrize("variant", PAIRSV_VARIANTS)
def test_pairsv_ladder_forward_shapes(variant, inputs):
    model = PairSV(variant, candidate_dim=32, read_dim=24, pileup_dim=16, branch_dim=12, fusion_dim=20)
    model.eval()
    kwargs = {"images": inputs["images"]}
    if variant in {"M1", "M4"}:
        kwargs["candidate_features"] = inputs["candidate_features"]
    if variant in {"M3", "M4"}:
        kwargs["read_features"] = inputs["read_features"]
    if variant in {"M2", "M4"}:
        kwargs["scalar_features"] = inputs["scalar_features"]
    assert model(**kwargs).shape == (2, 2)


def test_m4_has_exactly_one_identity_at_initialization_mechanism(inputs):
    model = PairSV("M4", candidate_dim=32, read_dim=24, pileup_dim=16, branch_dim=12, fusion_dim=20)
    model.eval()
    with torch.no_grad():
        image_logits = model.image_classifier(model.image_features(inputs["images"]))
        fused_logits = model(**inputs)
    assert torch.equal(fused_logits, image_logits)
    assert model.residual_fusion[-1].weight.count_nonzero() == 0
    assert not any("gate" in name.lower() for name, _ in model.named_modules())


@pytest.mark.parametrize("variant", M4_ABLATION_VARIANTS)
def test_m4_retrained_ablation_variant_forward_shapes(variant, inputs):
    """Item 9's retrained branch-removal ablations: each omits exactly one of
    M4's three branches, structurally, as a genuine 2-branch model -- not a
    post-hoc zero/shuffle intervention on the trained M4."""
    model = PairSV(variant, candidate_dim=32, read_dim=24, pileup_dim=16, branch_dim=12, fusion_dim=20)
    model.eval()
    kwargs = {"images": inputs["images"]}
    if "candidate" in model.active_branches:
        kwargs["candidate_features"] = inputs["candidate_features"]
    if "read" in model.active_branches:
        kwargs["read_features"] = inputs["read_features"]
    if "scalar" in model.active_branches:
        kwargs["scalar_features"] = inputs["scalar_features"]
    assert len(model.active_branches) == 2
    assert model(**kwargs).shape == (2, 2)


@pytest.mark.parametrize("variant", M4_ABLATION_VARIANTS)
def test_m4_retrained_ablation_variant_identity_at_initialization(variant, inputs):
    model = PairSV(variant, candidate_dim=32, read_dim=24, pileup_dim=16, branch_dim=12, fusion_dim=20)
    model.eval()
    kwargs = {"images": inputs["images"]}
    if "candidate" in model.active_branches:
        kwargs["candidate_features"] = inputs["candidate_features"]
    if "read" in model.active_branches:
        kwargs["read_features"] = inputs["read_features"]
    if "scalar" in model.active_branches:
        kwargs["scalar_features"] = inputs["scalar_features"]
    with torch.no_grad():
        image_logits = model.image_classifier(model.image_features(inputs["images"]))
        fused_logits = model(**kwargs)
    assert torch.equal(fused_logits, image_logits)
    assert model.residual_fusion[-1].weight.count_nonzero() == 0


def test_m4_branch_ablation_and_input_validation(inputs):
    model = PairSV("M4", candidate_dim=32, read_dim=24, pileup_dim=16, branch_dim=12, fusion_dim=20)
    model.eval()
    assert model(**inputs, ablate={"read"}).shape == (2, 2)
    with pytest.raises(ValueError, match="requires read_features"):
        model(
            inputs["images"],
            candidate_features=inputs["candidate_features"],
            scalar_features=inputs["scalar_features"],
        )
    with pytest.raises(ValueError, match="cannot ablate"):
        model(**inputs, ablate={"population"})
