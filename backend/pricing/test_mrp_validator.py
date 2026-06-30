import pytest
from backend.pricing.mrp_validator import apply_mrp_limit

def test_mrp_below_limit():
    # Case 1: Calculated price is below MRP -> expected: no capping
    res = apply_mrp_limit(calculated_price=110.0, mrp=120.0)
    assert res["final_price"] == 110.0
    assert res["calculated_price"] == 110.0
    assert res["mrp"] == 120.0
    assert res["mrp_limit_applied"] is False

def test_mrp_above_limit():
    # Case 2: Calculated price is above MRP -> expected: capping to MRP applied
    res = apply_mrp_limit(calculated_price=135.0, mrp=120.0)
    assert res["final_price"] == 120.0
    assert res["calculated_price"] == 135.0
    assert res["mrp"] == 120.0
    assert res["mrp_limit_applied"] is True

def test_mrp_equal_to_limit():
    # Case 3: Calculated price is exactly equal to MRP -> expected: no capping
    res = apply_mrp_limit(calculated_price=120.0, mrp=120.0)
    assert res["final_price"] == 120.0
    assert res["calculated_price"] == 120.0
    assert res["mrp"] == 120.0
    assert res["mrp_limit_applied"] is False

def test_invalid_mrp_strict():
    # Case 4: Zero or negative MRP in strict mode -> expected: raise ValueError
    with pytest.raises(ValueError):
        apply_mrp_limit(calculated_price=50.0, mrp=0.0, strict=True)
    with pytest.raises(ValueError):
        apply_mrp_limit(calculated_price=50.0, mrp=-10.0, strict=True)
    with pytest.raises(ValueError):
        apply_mrp_limit(calculated_price=50.0, mrp=None, strict=True)

def test_invalid_mrp_non_strict():
    # Case 5: Zero or negative MRP in non-strict mode -> expected: log warning & skip validation
    res = apply_mrp_limit(calculated_price=50.0, mrp=0.0, strict=False)
    assert res["final_price"] == 50.0
    assert res["mrp_limit_applied"] is False

    res = apply_mrp_limit(calculated_price=50.0, mrp=-1.0, strict=False)
    assert res["final_price"] == 50.0
    assert res["mrp_limit_applied"] is False
