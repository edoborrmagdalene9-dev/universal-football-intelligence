"""Offline demo using synthetic data only."""
from .optimizer import Player, RosterRules, optimize_lineup


def main() -> None:
    players = [
        Player("a", "Demo Forward A", "A", "FWD", 9000, 18.2),
        Player("b", "Demo Forward B", "B", "FWD", 8200, 16.1),
        Player("c", "Demo Midfielder A", "A", "MID", 7600, 13.4),
        Player("d", "Demo Midfielder B", "C", "MID", 6800, 11.9),
        Player("e", "Demo Defender A", "B", "DEF", 5400, 8.1),
        Player("f", "Demo Defender B", "C", "DEF", 4900, 7.4),
        Player("g", "Demo Goalkeeper", "D", "GK", 4300, 6.2),
    ]
    rules = RosterRules(5, 30000, {"FWD": (1, 2), "MID": (1, 2), "DEF": (1, 2), "GK": (1, 1)}, 2)
    lineup = optimize_lineup(players, rules)
    print("SYNTHETIC DEMO ONLY — not real fixtures or advice")
    for p in lineup:
        print(f"{p.position:4} {p.name:20} salary={p.salary} projection={p.projection}")
    print("Salary:", sum(p.salary for p in lineup))
    print("Projected points:", round(sum(p.projection for p in lineup), 2))


if __name__ == "__main__":
    main()
