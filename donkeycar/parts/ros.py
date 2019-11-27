import rospy
from std_msgs.msg import String, Int32, Float32

'''
sudo apt-get install python3-catkin-pkg

ROS issues w python3:
https://discourse.ros.org/t/should-we-warn-new-users-about-difficulties-with-python-3-and-alternative-python-interpreters/3874/3
'''

class RosPubisher(object):
    '''
    A ROS node to pubish to a data stream
    '''
    def __init__(self, node_name, channel_name, stream_type=String, anonymous=True):
        self.data = ""
        self.pub = rospy.Publisher(channel_name, stream_type)
        rospy.init_node(node_name, anonymous=anonymous)

    def run(self, data):
        '''
        only publish when data stream changes.
        '''
        if data != self.data and not rospy.is_shutdown():
            self.data = data
            self.pub.publish(data)
    

class RosSubscriber(object):
    '''
    A ROS node to subscribe to a data stream
    '''

    def __init__(self, node_name, channel_name, stream_type=String, anonymous=True):
        self.data = ""
        rospy.init_node(node_name, anonymous=anonymous)
        self.pub = rospy.Subscriber(channel_name, stream_type, self.on_data_recv)        

    def on_data_recv(self, data):
        self.data = data.data

    def run(self):
        return self.data

