import unittest
from core.signal_processing import SignalProcessor

class TestSignalProcessor(unittest.TestCase):
    def setUp(self):
        self.sp = SignalProcessor(window_size=5, max_capacity=100, max_duration_frames=300)

    def test_moving_average(self):
        # Test the causal low-pass filter (moving average)
        # Input step response
        self.sp.moving_average(10, self.sp.density_buffer)
        self.sp.moving_average(10, self.sp.density_buffer)
        self.assertEqual(self.sp.moving_average(10, self.sp.density_buffer), 10.0)
        
        self.sp.moving_average(20, self.sp.density_buffer)
        self.assertEqual(self.sp.moving_average(20, self.sp.density_buffer), 14.0) # (10+10+10+20+20)/5 = 14

    def test_risk_calculation(self):
        # R[n] = 0.45D + 0.35C + 0.20T
        # Test max values
        risk = self.sp.calculate_risk(100, 100, 100, 0.45, 0.35, 0.20)
        self.assertAlmostEqual(risk, 100.0)

        # Test partial
        risk = self.sp.calculate_risk(50, 50, 0, 0.45, 0.35, 0.20)
        self.assertAlmostEqual(risk, 40.0)

    def test_risk_categories(self):
        self.assertEqual(self.sp.get_risk_category(20, 30, 60), "Safe")
        self.assertEqual(self.sp.get_risk_category(45, 30, 60), "Warning")
        self.assertEqual(self.sp.get_risk_category(75, 30, 60), "High Risk")

if __name__ == '__main__':
    unittest.main()
