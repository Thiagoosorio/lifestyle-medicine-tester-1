import components.organ_health_display as organ_health_display
import models.clinical_profile as clinical_profile


def test_partial_profile_stores_omitted_fields_as_unknown(db_conn, test_user):
    supplied = {"sex": "female", "on_statin": 0}
    assert set(clinical_profile.PROFILE_DEFAULTS) == set(clinical_profile.PROFILE_FIELDS)
    assert all(value is None for value in clinical_profile.PROFILE_DEFAULTS.values())

    clinical_profile.save_profile(test_user, supplied)

    profile = clinical_profile.get_profile(test_user)
    assert profile is not None
    for field in clinical_profile.PROFILE_FIELDS:
        assert profile[field] == supplied.get(field)


def test_explicit_low_risk_values_remain_distinct_from_unknown(db_conn, test_user):
    supplied = {
        "ethnicity": "white",
        "height_cm": 170.0,
        "weight_kg": 70.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
        "diabetes_status": 0,
        "diabetes_type": "none",
        "family_history_chd": 0,
        "atrial_fibrillation": 0,
        "rheumatoid_arthritis": 0,
        "education_years": 12,
        "physical_activity_level": "active",
    }

    clinical_profile.save_profile(test_user, supplied)

    profile = clinical_profile.get_profile(test_user)
    assert profile is not None
    assert {field: profile[field] for field in supplied} == supplied
    assert profile["chronic_kidney_disease"] is None


def test_partial_update_preserves_existing_supplied_values(db_conn, test_user):
    original = {
        "sex": "male",
        "ethnicity": "black_african",
        "height_cm": 180.0,
        "weight_kg": 82.0,
        "systolic_bp": 138.0,
        "diastolic_bp": 86.0,
        "diabetes_status": 1,
        "diabetes_type": "type2",
        "family_history_chd": 1,
        "education_years": 16,
        "physical_activity_level": "inactive",
    }
    clinical_profile.save_profile(test_user, original)

    clinical_profile.save_profile(test_user, {"weight_kg": 80.0})

    profile = clinical_profile.get_profile(test_user)
    assert profile is not None
    assert profile["weight_kg"] == 80.0
    for field, value in original.items():
        if field != "weight_kg":
            assert profile[field] == value


class _FakeStreamlit:
    def __init__(self, *, select_values=None, number_values=None, submitted=False):
        self.selected = {}
        self.numbers = {}
        self.errors = []
        self._select_values = select_values or {}
        self._number_values = number_values or {}
        self._submitted = submitted

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def form(self, **_kwargs):
        return self

    def expander(self, *_args, **_kwargs):
        return self

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [self for _ in range(count)]

    def markdown(self, *_args, **_kwargs):
        return None

    def caption(self, *_args, **_kwargs):
        return None

    def date_input(self, _label, *, value=None, **_kwargs):
        return value

    def selectbox(self, label, *, options, index=0, **_kwargs):
        selected = self._select_values.get(label, options[index])
        self.selected[label] = selected
        return selected

    def number_input(self, label, *, value=None, **_kwargs):
        number = self._number_values.get(label, value)
        self.numbers[label] = number
        return number

    def form_submit_button(self, *_args, **_kwargs):
        return self._submitted

    def error(self, message):
        self.errors.append(message)


def test_new_profile_form_has_no_plausible_clinical_defaults(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(organ_health_display, "st", fake_st)
    monkeypatch.setattr(organ_health_display, "get_profile", lambda _user_id: None)

    organ_health_display.render_clinical_profile_form(123)

    assert fake_st.selected["Ethnicity"] is None
    assert fake_st.selected["Diabetes Type"] is None
    assert fake_st.selected["Physical activity level"] is None
    assert fake_st.selected["Atrial fibrillation"] is None
    assert fake_st.selected["Chronic kidney disease (stage 3-5)"] is None
    assert fake_st.numbers["Height (cm)"] is None
    assert fake_st.numbers["Weight (kg)"] is None
    assert fake_st.numbers["Systolic BP (mmHg)"] is None
    assert fake_st.numbers["Diastolic BP (mmHg)"] is None
    assert fake_st.numbers["Education (total years)"] is None


def test_current_smoker_requires_explicit_cigarette_count(monkeypatch):
    fake_st = _FakeStreamlit(
        select_values={"Smoking Status": "current"},
        submitted=True,
    )
    saved = []
    monkeypatch.setattr(organ_health_display, "st", fake_st)
    monkeypatch.setattr(organ_health_display, "get_profile", lambda _user_id: None)
    monkeypatch.setattr(clinical_profile, "save_profile", lambda *args: saved.append(args))

    organ_health_display.render_clinical_profile_form(123)

    assert fake_st.errors == ["Enter cigarettes per day for a current smoker."]
    assert saved == []
