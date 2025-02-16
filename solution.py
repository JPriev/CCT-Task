from dataclasses import dataclass, field
from enum import Enum


class Action(Enum):
    PICKUP = 'pick'
    DROP = 'drop'
    START = 'start'
    END = 'end'


@dataclass(frozen=True)
class Package:
    id: int
    pickup: int
    drop: int
    weight: int

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(
                f'Package weight must be positive, got {self.weight}')
        if self.pickup == self.drop:
            raise ValueError('Pickup and drop locations cannot be the same')

    def __eq__(self, other) -> bool:
        if not isinstance(other, Package):
            raise ValueError(f'Object type must be Package not {type(other)}')

        return self.id == other.id


@dataclass
class Van:
    capacity: int
    fuel_consumption: int
    cargo: list[Package] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(
                f'Van capacity must be positive, got {self.capacity}')
        if self.fuel_consumption <= 0:
            raise ValueError(
                f'Fuel consumption must be positive, got {self.fuel_consumption}')

    @property
    def current_weight(self) -> int:
        return sum(package.weight for package in self.cargo)

    @property
    def van_info(self) -> tuple[int, int]:
        return (self.capacity, self.fuel_consumption)

    def can_fit_package(self, package: Package) -> bool:
        return self.current_weight + package.weight <= self.capacity

    def has_package(self, package: Package) -> bool:
        return package in self.cargo


@dataclass
class Location:
    location: int
    action: Action
    package: Package | None

    @property
    def is_pickup(self) -> bool:
        return self.action == Action.PICKUP

    @property
    def is_drop(self) -> bool:
        return self.action == Action.DROP


@dataclass
class DeliveryRoute:
    van: Van
    visited_locations: list[Location]
    all_locations: list[Location]

    @property
    def available_locations(self) -> list[Location]:
        return [loc for loc in self.all_locations if loc not in self.visited_locations]

    @property
    def route_length(self) -> int:
        return sum(
            abs(curr_loc.location - next_loc.location)
            for curr_loc, next_loc in zip(self.visited_locations, self.visited_locations[1:])
        )

    @property
    def fuel_consumption(self) -> int:
        return self.route_length * self.van.fuel_consumption

    @property
    def formated_locations(self) -> list[tuple[int, str]]:
        return [(loc.location, loc.action.value) for loc in self.visited_locations]

    # Used for debuging
    @property
    def locations(self) -> list[int]:
        return [location.location for location in self.visited_locations]

    def get_valid_locations(self) -> list[Location]:
        valid_locations = []

        for available_location in self.available_locations:
            if available_location.is_pickup:
                if (not self.van.has_package(available_location.package) and
                        self.van.can_fit_package(available_location.package)):
                    valid_locations.append(available_location)

            elif available_location.is_drop:
                if self.van.has_package(available_location.package):
                    valid_locations.append(available_location)

        return valid_locations


def get_suitable_vans(
    vans: list[Van],
    packages: list[Package]
) -> list[Van]:
    max_package_weight = max(package.weight for package in packages)
    suitable_vans = [
        van for van in vans
        if van.capacity >= max_package_weight
    ]

    return suitable_vans


def generate_locations(packages: list[Package]) -> tuple[list[Location], Location, Location]:
    pickup_locations = [
        Location(
            location=package.pickup,
            action=Action.PICKUP,
            package=package,
        )
        for package in packages
    ]

    drop_locations = [
        Location(
            location=package.drop,
            action=Action.DROP,
            package=package,
        )
        for package in packages
    ]

    start_location = Location(location=0, action=Action.START, package=None)
    end_location = Location(location=0, action=Action.END, package=None)

    return pickup_locations + drop_locations, start_location, end_location


def generate_all_possible_routes_for_van(packages: list[Package], van: Van) -> list[Location]:
    all_locations, start_point, end_point = generate_locations(packages)

    routes: list[DeliveryRoute] = []

    for location in all_locations:
        if location.is_pickup:
            new_van = Van(
                capacity=van.capacity,
                fuel_consumption=van.fuel_consumption,
                cargo=[location.package],
            )
            routes.append(
                DeliveryRoute(
                    van=new_van,
                    visited_locations=[start_point, location],
                    all_locations=all_locations,
                )
            )

    for _ in range(len(packages) * 2 - 1):
        routes = update_routes(routes)

    for route in routes:
        route.visited_locations += [end_point]

    return routes


def update_routes(routes: list[DeliveryRoute]) -> list[DeliveryRoute]:
    def generate_new_route(current_route: DeliveryRoute, location: Location) -> DeliveryRoute:
        new_cargo = current_route.van.cargo.copy()

        if location.is_pickup:
            new_cargo.append(location.package)
        elif location.is_drop:
            new_cargo.remove(location.package)

        new_van = Van(
            capacity=current_route.van.capacity,
            fuel_consumption=current_route.van.fuel_consumption,
            cargo=new_cargo,
        )

        new_route = DeliveryRoute(
            van=new_van,
            visited_locations=current_route.visited_locations + [location],
            all_locations=current_route.all_locations,
        )

        return new_route

    new_routes = []
    for route in routes:
        valid_locations = route.get_valid_locations()
        if not valid_locations:
            continue

        for valid_location in valid_locations:
            new_routes.append(generate_new_route(route, valid_location))

    return new_routes if new_routes else routes


def find_optimal_route_for_single_van(van_stats: list[tuple[int, int]], packages: list[tuple[int, int, int]]) -> tuple[
        tuple[int, int], list[tuple[int, str]], int, int]:
    vans = [Van(v[0], v[1]) for v in van_stats]
    packages = [Package(i, p[0], p[1], p[2]) for i, p in enumerate(packages)]

    suitable_vans = get_suitable_vans(vans, packages)
    if not suitable_vans:
        raise ValueError('No vans capable of carrying all packages')

    optimal_routes: list[DeliveryRoute] = [
        min(generate_all_possible_routes_for_van(packages, van),
            key=lambda r: r.fuel_consumption)
        for van in suitable_vans
    ]

    if not optimal_routes:
        raise ValueError('No valid routes found')

    best_route: DeliveryRoute = min(
        optimal_routes, key=lambda r: r.fuel_consumption)

    return (
        best_route.van.van_info,
        best_route.formated_locations,
        best_route.route_length,
        best_route.fuel_consumption,
    )


if __name__ == "__main__":
    selected_van, optimal_route, route_length, fuel_consumption = find_optimal_route_for_single_van(
        [(10, 10), (9, 8)],  [(-1, 5, 4), (6, 2, 9), (-2, 9, 3)]
    )

    assert selected_van == (9, 8)
    assert optimal_route == [
        (0, 'start'), (-1, 'pick'), (-2, 'pick'), (5, 'drop'),
        (9, 'drop'), (6, 'pick'), (2, 'drop'), (0, 'end')
    ]
    assert route_length == 22
    assert fuel_consumption == 176

    print("ALL TESTS PASSED")
