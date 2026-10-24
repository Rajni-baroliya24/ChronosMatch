# ChronosMatch Synthetic Market Data & Test Fixture Generator
# Author: Gauri Dwivedi
# Role: Testing & Performance Benchmarking Lead

import json
import random

def generate_hft_mock_ticks(count=100):
    """Generates synthetic high-frequency trading ticks for benchmark testing."""
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    ticks = []
    
    for i in range(count):
        base_price = random.choice([65000.0, 3500.0, 150.0])
        tick = {
            "tick_id": i + 1,
            "symbol": random.choice(symbols),
            "bid": round(base_price, 2),
            "ask": round(base_price + random.uniform(0.1, 2.0), 2),
            "volume": random.randint(1, 50)
        }
        ticks.append(tick)
    return ticks

if __name__ == "__main__":
    print("[MOCK GEN] Generating 100 HFT market data ticks...")
    data = generate_hft_mock_ticks(100)
    
    with open("mock_market_data.json", "w") as f:
        json.dump(data, f, indent=2)
        
    print("[SUCCESS] Saved synthetic test fixtures to mock_market_data.json")
