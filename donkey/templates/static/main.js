

var driveHandler = (function() {
    //functions used to drive the vehicle. 

    var angle = 0
    var throttle = 0
    var driveMode = 'user'
    var recording = false
    var pilot = 'None'

    var angleEl = "#angleInput"
    var throttleEl = "#throttleInput"

    var joystick_options = {}
    var joystickLoopRunning=false;   
    var vehicle_id = ""
    var driveURL = ""
    var vehicleURL = ""

    var load = function() {

      vehicle_id = $('#vehicle_id').data('id') 
      driveURL = '/api/vehicles/drive/' + vehicle_id + "/"
      vehicleURL = '/api/vehicles/' + vehicle_id + "/"

      bindKeys()
      bindPilotSelect()

      joystick_options = {
        zone: document.getElementById('joystick_container'),  // active zone
        color: '#668AED',
        size: 350,
      };

      var manager = nipplejs.create(joystick_options);
      
      bindNipple(manager)

      if(!!navigator.getGamepads){
         gamePadLoop(); 
      }

    };



    var bindKeys = function() {
      //Bind a function to capture the coordinates of the click.
      $(angleEl).change(function(e) {
          postDrive()
      });
      $(throttleEl).change(function(e) {
          postDrive()
      });

      $(document).keydown(function(e) {
          if(e.which == 73) {
            // 'i'  throttle up
              throttleUp()
          } 

          if(e.which == 75) {
            // 'k'  slow down
              throttleDown()
          }

          if(e.which == 74) {
            // 'j' turn left
              angleLeft()
          }

          if(e.which == 76) {
            // 'l' turn right
              angleRight()
          }

          if(e.which == 65) {
            // 'a' turn on auto mode
              updateDriveMode('auto')
          }
          if(e.which == 68) {
            // 'a' turn on auto mode
              updateDriveMode('user')
          }
            if(e.which == 83) {
            // 'a' turn on auto mode
              updateDriveMode('auto_angle')
          }
      });
    };


    function bindNipple(manager) {
      manager.on('start end', function(evt, data) {
        $('#angleInput').val(0);
        $('#throttleInput').val(0);

        if (!joystickLoopRunning) {
          joystickLoopRunning=true;
          joystickLoop();
        } else {
          joystickLoopRunning=false;
        }

      }).on('move', function(evt, data) {
        radian = data['angle']['radian']
        distance = data['distance']

        //console.log(data)

        angle = Math.round(distance * Math.cos(radian)/2)
        throttle = Math.round(distance/joystick_options['size']*200)
        
        if (data['angle']['degree'] > 180 ){
          throttle = throttle * -1
        }

        recording = true

      });
    }


    var bindPilotSelect = function(){
        $('#pilot_select').on('change', function () {
                  pilot = $(this).val(); // get selected value
                  postPilot()
              });
    };


    var postPilot = function(){
        data = JSON.stringify({ 'pilot': pilot })
        $.post(vehicleURL, data)
    }


    var updateDisplay = function() {
      $(throttleEl).val(throttle);
      $(angleEl).val(angle);
      $('#driveMode').val(driveMode);
    };

    var postDrive = function() {
        //Send angle and throttle values
        updateDisplay()
        data = JSON.stringify({ 'angle': angle, 'throttle':throttle, 
          'drive_mode':driveMode, 'recording': recording})
        console.log(data)
        $.post(driveURL, data)
    };

var applyDeadzone = function(number, threshold){
   percentage = (Math.abs(number) - threshold) / (1 - threshold);

   if(percentage < 0)
      percentage = 0;

   return percentage * (number > 0 ? 1 : -1);
}

    function gamePadLoop()
    {
       setTimeout(gamePadLoop,100);

    var gamepads = navigator.getGamepads();

    for (var i = 0; i < gamepads.length; ++i)
    {
        var pad = gamepads[i];
        // some pads are NULL I think.. some aren't.. use one that isn't null
        if (pad && pad.timestamp!=0)
        {
        	var joystickX = applyDeadzone(pad.axes[2], 0.05);
        	//console.log(joystickX);
        	angle = joystickX * 90;
        	//console.log('angle:'+angle);
        	var joystickY = applyDeadzone(pad.axes[1], 0.15);
        	//console.log(joystickY);
        	throttle= joystickY * -100 ;
        	//console.log('throttle:'+throttle);
        	if (throttle> 10 || throttle<-10)
                  recording = true
        	else 
                  recording = false

            postDrive()
	}
        // todo; simple demo of displaying pad.axes and pad.buttons
    }
   }

    // Send control updates to the server every .1 seconds.
    function joystickLoop () {           
       setTimeout(function () {    
            postDrive()

          if (joystickLoopRunning) {      
             joystickLoop();             
          } else {
            // Send zero angle, throttle and stop recording
            angle = 0
            throttle = 0
            recording = false
            postDrive()
          }
       }, 100)
    }

    var throttleUp = function(){
        //Bind a function to capture the coordinates of the click.
        throttle = Math.min(throttle + 5, 400);
        postDrive()
        };

    var throttleDown = function(){
        //Bind a function to capture the coordinates of the click.
        throttle = Math.max(throttle - 10, -200);
        postDrive()
    };

    var angleLeft = function(){
      //Bind a function to capture the coordinates of the click.
      angle = Math.max(angle - 10, -90)
      postDrive()
    };

    var angleRight = function(){
      //Bind a function to capture the coordinates of the click.
      angle = Math.min(angle + 10, 90)
      postDrive()
    };

    var updateDriveMode = function(mode){
      //Bind a function to capture the coordinates of the click.
      driveMode = mode;
      postDrive()
    };


    return {  load: load };
})();
