import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Float32
import time
import board
import busio
from adafruit_bno08x import BNO_REPORT_ACCELEROMETER, BNO_REPORT_GYROSCOPE, BNO_REPORT_ROTATION_VECTOR, BNO_REPORT_MAGNETOMETER
from adafruit_bno08x.i2c import BNO08X_I2C

class IMUPublisher(Node):
    def __init__(self):
        super().__init__('imu_driver')
        self.logger = self.get_logger()
        self.declare_parameters(
            namespace='',
            parameters=[
                ('i2c_address', 0x4b),
                ('enable_imu', True),
                ('enable_magnetometer', False),
                ('imu_rate', 100),
                ('magnetometer_rate', 100),
            ]
        )

        self.imu_publisher = self.create_publisher(Imu, '/sensor/imu/data', 10)

        # Initialize sensor
        self.sensor = self.initialize_sensor()

        # Setup timer for IMU data publishing
        imu_rate = self.get_parameter('imu_rate').value
        self.create_timer(1.0 / imu_rate, self.publish_imu_data)

        # Setup timer for magnetometer data publishing if enabled
        if self.get_parameter('enable_magnetometer').value:
            self.logger.info("Enabling Magnetometer")
            self.magnetic_field_publisher = self.create_publisher(MagneticField, '/sensor/imu/magnetic_field', 10)
            magnetometer_rate = self.get_parameter('magnetometer_rate').value
            self.create_timer(1.0 / magnetometer_rate, self.publish_magnetic_field_data)
        self.logger.info("IMU Driver node initialized")

    def initialize_sensor(self):
        address = self.get_parameter('i2c_address').value
        i2c = busio.I2C(board.SCL, board.SDA)
        bno = BNO08X_I2C(i2c, address=address)
        bno.enable_feature(BNO_REPORT_ACCELEROMETER)
        bno.enable_feature(BNO_REPORT_GYROSCOPE)
        bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
        if self.get_parameter('enable_magnetometer').value:
            bno.enable_feature(BNO_REPORT_MAGNETOMETER)
        self.logger.info("BNO085 IMU sensor initialized")
        return bno

    def publish_imu_data(self):
        # Fetch data from sensor
        acceleration = self.sensor.acceleration
        gyro = self.sensor.gyro
        rotation = self.sensor.quaternion

        # Prepare IMU message
        imu_msg = Imu()
        imu_msg.header.stamp = self.get_clock().now().to_msg()
        imu_msg.header.frame_id = "imu_link"
        imu_msg.linear_acceleration.x, imu_msg.linear_acceleration.y, imu_msg.linear_acceleration.z = acceleration
        imu_msg.angular_velocity.x, imu_msg.angular_velocity.y, imu_msg.angular_velocity.z = gyro
        imu_msg.orientation.x, imu_msg.orientation.y, imu_msg.orientation.z, imu_msg.orientation.w = rotation

        # Publish the IMU message
        self.imu_publisher.publish(imu_msg)

    def publish_magnetic_field_data(self):
        # Fetch data from sensor
        magnetic_field = self.sensor.magnetic

        # Prepare MagneticField message
        mag_msg = MagneticField()
        mag_msg.header.stamp = self.get_clock().now().to_msg()
        mag_msg.header.frame_id = "imu_link"
        mag_msg.magnetic_field.x, mag_msg.magnetic_field.y, mag_msg.magnetic_field.z = magnetic_field

        # Publish the MagneticField message
        self.magnetic_field_publisher.publish(mag_msg)

def main(args=None):
    rclpy.init(args=args)
    imu_publisher = IMUPublisher()

    executor = SingleThreadedExecutor()
    executor.add_node(imu_publisher)

    try:
        executor.spin()
    finally:
        imu_publisher.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
