from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from territory.models import District, VotingDesk, Building


class DistrictModelTests(TestCase):
    """Tests for the District model."""

    def test_create_district(self):
        """Test creating a district with all fields."""
        district = District.objects.create(
            name="Lyon 6ème",
            code="69006",
            description="6ème arrondissement de Lyon"
        )
        self.assertEqual(district.name, "Lyon 6ème")
        self.assertEqual(district.code, "69006")
        self.assertEqual(district.description, "6ème arrondissement de Lyon")

    def test_district_str_representation(self):
        """Test the string representation of a district."""
        district = District.objects.create(
            name="Lyon 6ème",
            code="69006"
        )
        self.assertEqual(str(district), "Lyon 6ème")

    def test_district_code_unique(self):
        """Test that district code must be unique."""
        District.objects.create(name="Lyon 6ème", code="69006")
        with self.assertRaises(IntegrityError):
            District.objects.create(name="Another District", code="69006")

    def test_district_description_optional(self):
        """Test that description is optional."""
        district = District.objects.create(
            name="Lyon 7ème",
            code="69007"
        )
        self.assertEqual(district.description, "")


class VotingDeskModelTests(TestCase):
    """Tests for the VotingDesk model."""

    def setUp(self):
        """Create a district for testing."""
        self.district = District.objects.create(
            name="Lyon 6ème",
            code="69006",
            description="6ème arrondissement"
        )

    def test_create_voting_desk(self):
        """Test creating a voting desk linked to a district."""
        voting_desk = VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=self.district
        )
        self.assertEqual(voting_desk.name, "Bureau 601")
        self.assertEqual(voting_desk.code, "BV601")
        self.assertEqual(voting_desk.district, self.district)

    def test_voting_desk_str_representation(self):
        """Test the string representation of a voting desk."""
        voting_desk = VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=self.district
        )
        self.assertEqual(str(voting_desk), "Bureau 601")

    def test_voting_desk_code_unique(self):
        """Test that voting desk code must be unique."""
        VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=self.district
        )
        with self.assertRaises(IntegrityError):
            VotingDesk.objects.create(
                name="Another Bureau",
                code="BV601",
                district=self.district
            )

    def test_voting_desk_district_relationship(self):
        """Test accessing voting desks from district."""
        VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=self.district
        )
        VotingDesk.objects.create(
            name="Bureau 602",
            code="BV602",
            district=self.district
        )
        self.assertEqual(self.district.voting_desks.count(), 2)

    def test_voting_desk_cascade_delete(self):
        """Test that deleting a district cascades to voting desks."""
        VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=self.district
        )
        self.assertEqual(VotingDesk.objects.count(), 1)
        self.district.delete()
        self.assertEqual(VotingDesk.objects.count(), 0)


class BuildingModelTests(TestCase):
    """Tests for the Building model."""

    def setUp(self):
        """Create district and voting desk for testing."""
        self.district = District.objects.create(
            name="Lyon 6ème",
            code="69006"
        )
        self.voting_desk = VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=self.district
        )

    def test_create_building(self):
        """Test creating a building linked to a voting desk."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=self.voting_desk
        )
        self.assertEqual(building.street_number, "12")
        self.assertEqual(building.street_name, "Rue de la République")
        self.assertEqual(building.num_electors, 45)
        self.assertEqual(building.voting_desk, self.voting_desk)

    def test_building_str_representation(self):
        """Test the string representation of a building."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=self.voting_desk
        )
        self.assertEqual(str(building), "12 Rue de la République")

    def test_building_voting_desk_relationship(self):
        """Test accessing buildings from voting desk."""
        Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=self.voting_desk
        )
        Building.objects.create(
            street_number="14",
            street_name="Rue de la République",
            num_electors=30,
            voting_desk=self.voting_desk
        )
        self.assertEqual(self.voting_desk.buildings.count(), 2)

    def test_building_cascade_delete(self):
        """Test that deleting a voting desk cascades to buildings."""
        Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=self.voting_desk
        )
        self.assertEqual(Building.objects.count(), 1)
        self.voting_desk.delete()
        self.assertEqual(Building.objects.count(), 0)

    def test_building_full_cascade_from_district(self):
        """Test that deleting a district cascades through voting desk to buildings."""
        Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=self.voting_desk
        )
        self.assertEqual(Building.objects.count(), 1)
        self.assertEqual(VotingDesk.objects.count(), 1)
        self.district.delete()
        self.assertEqual(Building.objects.count(), 0)
        self.assertEqual(VotingDesk.objects.count(), 0)

    def test_building_num_electors_default(self):
        """Test that num_electors defaults to 0."""
        building = Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            voting_desk=self.voting_desk
        )
        self.assertEqual(building.num_electors, 0)

    def test_building_unique_together(self):
        """Test that street_number + street_name + voting_desk must be unique together."""
        Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            voting_desk=self.voting_desk
        )
        with self.assertRaises(IntegrityError):
            Building.objects.create(
                street_number="12",
                street_name="Rue de la République",
                voting_desk=self.voting_desk
            )


class HierarchyIntegrationTests(TestCase):
    """Integration tests for the full hierarchy."""

    def test_full_hierarchy_creation(self):
        """Test creating a complete hierarchy: District -> VotingDesk -> Building."""
        district = District.objects.create(
            name="Lyon 6ème",
            code="69006",
            description="6ème arrondissement de Lyon"
        )
        voting_desk = VotingDesk.objects.create(
            name="Bureau 601",
            code="BV601",
            district=district
        )
        building = Building.objects.create(
            street_number="12",
            street_name="Rue de la République",
            num_electors=45,
            voting_desk=voting_desk
        )

        # Verify relationships
        self.assertEqual(building.voting_desk, voting_desk)
        self.assertEqual(voting_desk.district, district)
        self.assertEqual(building.voting_desk.district, district)

    def test_district_total_buildings(self):
        """Test counting all buildings in a district across voting desks."""
        district = District.objects.create(name="Lyon 6ème", code="69006")

        vd1 = VotingDesk.objects.create(name="Bureau 601", code="BV601", district=district)
        vd2 = VotingDesk.objects.create(name="Bureau 602", code="BV602", district=district)

        Building.objects.create(street_number="12", street_name="Rue A", voting_desk=vd1)
        Building.objects.create(street_number="14", street_name="Rue A", voting_desk=vd1)
        Building.objects.create(street_number="1", street_name="Rue B", voting_desk=vd2)

        # Count buildings in district via voting desks
        total_buildings = Building.objects.filter(voting_desk__district=district).count()
        self.assertEqual(total_buildings, 3)

    def test_district_total_electors(self):
        """Test summing all electors in a district."""
        district = District.objects.create(name="Lyon 6ème", code="69006")

        vd1 = VotingDesk.objects.create(name="Bureau 601", code="BV601", district=district)
        vd2 = VotingDesk.objects.create(name="Bureau 602", code="BV602", district=district)

        Building.objects.create(street_number="12", street_name="Rue A", num_electors=50, voting_desk=vd1)
        Building.objects.create(street_number="14", street_name="Rue A", num_electors=30, voting_desk=vd1)
        Building.objects.create(street_number="1", street_name="Rue B", num_electors=20, voting_desk=vd2)

        from django.db.models import Sum
        total_electors = Building.objects.filter(
            voting_desk__district=district
        ).aggregate(total=Sum('num_electors'))['total']
        self.assertEqual(total_electors, 100)
