from django.test import TestCase
from datetime import date

from mobilisation.models import Visit
from territory.models import District, VotingDesk, Building


class BuildingMobilisationTests(TestCase):
    """Tests for Building mobilisation fields."""

    def setUp(self):
        """Create territory hierarchy for testing."""
        self.district = District.objects.create(
            name="Lyon 5ème",
            code="5"
        )
        self.voting_desk = VotingDesk.objects.create(
            name="Bureau 502",
            code="502",
            location="Point du Jour",
            district=self.district
        )

    def test_building_is_finished_default_false(self):
        """Test that is_finished defaults to False."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue Test",
            voting_desk=self.voting_desk
        )
        self.assertFalse(building.is_finished)

    def test_building_mark_as_finished(self):
        """Test marking a building as finished."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue Test",
            voting_desk=self.voting_desk
        )
        building.is_finished = True
        building.save()
        building.refresh_from_db()
        self.assertTrue(building.is_finished)

    def test_building_geocoding_fields(self):
        """Test that building has geocoding fields."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue Test",
            voting_desk=self.voting_desk,
            latitude=45.7578,
            longitude=4.8320
        )
        self.assertEqual(building.latitude, 45.7578)
        self.assertEqual(building.longitude, 4.8320)

    def test_building_full_address_property(self):
        """Test the full_address property."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            voting_desk=self.voting_desk
        )
        self.assertEqual(building.full_address, "12 Rue de la République, Lyon")


class VisitModelTests(TestCase):
    """Tests for the Visit model."""

    def setUp(self):
        """Create buildings for testing."""
        self.district = District.objects.create(name="Lyon 5ème", code="5")
        self.voting_desk = VotingDesk.objects.create(
            name="Bureau 502",
            code="502",
            location="Point du Jour",
            district=self.district
        )
        self.building1 = Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=self.voting_desk
        )
        self.building2 = Building.objects.create(
            street_number="14",
            street_name="Rue de la République",
            num_electors=30,
            voting_desk=self.voting_desk
        )

    def test_create_visit_single_building(self):
        """Test creating a visit for a single building."""
        visit = Visit.objects.create(
            open_doors=5,
            knocked_doors=10,
            comment="First visit"
        )
        visit.buildings.add(self.building1)

        self.assertEqual(visit.open_doors, 5)
        self.assertEqual(visit.knocked_doors, 10)
        self.assertEqual(visit.comment, "First visit")
        self.assertEqual(visit.buildings.count(), 1)
        self.assertIn(self.building1, visit.buildings.all())

    def test_create_visit_multiple_buildings(self):
        """Test creating a visit covering multiple buildings (shared entrance)."""
        visit = Visit.objects.create(
            open_doors=8,
            knocked_doors=15,
            comment="Shared entrance building"
        )
        visit.buildings.add(self.building1, self.building2)

        self.assertEqual(visit.buildings.count(), 2)
        self.assertIn(self.building1, visit.buildings.all())
        self.assertIn(self.building2, visit.buildings.all())

    def test_visit_date_defaults_to_today(self):
        """Test that visit date defaults to today."""
        visit = Visit.objects.create(open_doors=3, knocked_doors=5)
        self.assertEqual(visit.date, date.today())

    def test_visit_custom_date(self):
        """Test creating a visit with a custom date."""
        custom_date = date(2024, 1, 15)
        visit = Visit.objects.create(
            open_doors=3,
            knocked_doors=5,
            date=custom_date
        )
        self.assertEqual(visit.date, custom_date)

    def test_visit_str_representation(self):
        """Test the string representation of a visit."""
        visit = Visit.objects.create(
            open_doors=5,
            knocked_doors=10,
            date=date(2024, 6, 15)
        )
        self.assertIn("2024-06-15", str(visit))

    def test_visit_comment_optional(self):
        """Test that comment is optional."""
        visit = Visit.objects.create(open_doors=3, knocked_doors=5)
        self.assertEqual(visit.comment, "")

    def test_building_visits_reverse_relation(self):
        """Test accessing visits from a building."""
        visit1 = Visit.objects.create(open_doors=5, knocked_doors=10)
        visit1.buildings.add(self.building1)

        visit2 = Visit.objects.create(open_doors=3, knocked_doors=8)
        visit2.buildings.add(self.building1)

        self.assertEqual(self.building1.visits.count(), 2)

    def test_visit_open_rate(self):
        """Test the open_rate property."""
        visit = Visit.objects.create(open_doors=5, knocked_doors=10)
        self.assertEqual(visit.open_rate, 50.0)

    def test_visit_open_rate_zero_knocked(self):
        """Test open_rate when no doors knocked."""
        visit = Visit.objects.create(open_doors=0, knocked_doors=0)
        self.assertEqual(visit.open_rate, 0)


class BuildingVisitIntegrationTests(TestCase):
    """Integration tests for Building and Visit."""

    def setUp(self):
        """Create territory hierarchy."""
        self.district = District.objects.create(name="Lyon 5ème", code="5")
        self.voting_desk = VotingDesk.objects.create(
            name="Bureau 502",
            code="502",
            location="Point du Jour",
            district=self.district
        )

    def test_building_total_statistics(self):
        """Test calculating total statistics for a building."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue Test",
            voting_desk=self.voting_desk
        )

        Visit.objects.create(open_doors=5, knocked_doors=10).buildings.add(building)
        Visit.objects.create(open_doors=3, knocked_doors=8).buildings.add(building)
        Visit.objects.create(open_doors=2, knocked_doors=5).buildings.add(building)

        from django.db.models import Sum
        totals = building.visits.aggregate(
            total_open=Sum('open_doors'),
            total_knocked=Sum('knocked_doors')
        )
        self.assertEqual(totals['total_open'], 10)
        self.assertEqual(totals['total_knocked'], 23)

    def test_shared_entrance_statistics(self):
        """Test that a visit with multiple buildings shares the same stats."""
        bldg1 = Building.objects.create(
            street_number="10",
            street_name="Rue A",
            voting_desk=self.voting_desk
        )
        bldg2 = Building.objects.create(
            street_number="12",
            street_name="Rue A",
            voting_desk=self.voting_desk
        )

        # Single visit for shared entrance
        visit = Visit.objects.create(
            open_doors=15,
            knocked_doors=30,
            comment="Shared entrance for 10 and 12"
        )
        visit.buildings.add(bldg1, bldg2)

        # Both buildings see the same visit
        self.assertEqual(bldg1.visits.first(), visit)
        self.assertEqual(bldg2.visits.first(), visit)
        self.assertEqual(bldg1.visits.first().open_doors, 15)

    def test_filter_visits_by_voting_desk(self):
        """Test filtering visits by voting desk."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue Test",
            voting_desk=self.voting_desk
        )
        visit = Visit.objects.create(open_doors=5, knocked_doors=10)
        visit.buildings.add(building)

        visits_in_desk = Visit.objects.filter(
            buildings__voting_desk=self.voting_desk
        ).distinct()
        self.assertEqual(visits_in_desk.count(), 1)

    def test_filter_visits_by_district(self):
        """Test filtering visits by district."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue Test",
            voting_desk=self.voting_desk
        )
        visit = Visit.objects.create(open_doors=5, knocked_doors=10)
        visit.buildings.add(building)

        visits_in_district = Visit.objects.filter(
            buildings__voting_desk__district=self.district
        ).distinct()
        self.assertEqual(visits_in_district.count(), 1)
