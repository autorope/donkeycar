##Connecting to AWS Donkey Instance

One way of setting up a server is to use Amazon to host it.  It is recommended that you use a g2.2xlarge instance in the nearest region. The g2 instances have GPUs which are useful for training with TensorFlow. While not tested, this will likely work on other GPU instances or elastic GPUs.  

Search under Community AMIs in "US-West(Northern California) for "donkey" you should find the following:

	donkey3 - ami-d8e6b6b8

For this to work the security group should be set up for:

* 	SSH
* 	Inbound TCP port 8887

Connect to the instance using SSH with the username "ubuntu". Directions on how to do this can be found [here](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AccessingInstancesLinux.html)

finally type the following to get the most recent update.

	cd donkey
	git pull origin master
	
