

var driveHandler = (function() {
    //functions used to drive the vehicle. 

    var state = {'tele': {
                          "user": {
                                  'angle': 0,
                                  'throttle': 0,
                                  },
                          "pilot": {
                                  'angle': 0,
                                  'throttle': 0,
                                  }
                          },
                  'brakeOn': true, 
                  'recording': false,
                  'driveMode': "user",
                  'pilot': 'None',
                  'session': 'None',
                  'lag': 0
                  }

    var joystick_options = {}
    var joystickLoopRunning=false;   

    var vehicle_id = ""
    var driveURL = ""
    var vehicleURL = ""

    var load = function() {

      vehicle_id = $('#vehicle_id').data('id') 
      driveURL = '/api/vehicles/drive/' + vehicle_id + "/"
      vehicleURL = '/api/vehicles/' + vehicle_id + "/"

      setBindings()

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



    var setBindings = function() {

      $(document).keydown(function(e) {
          if(e.which == 32) { brake() }  // 'space'  brake
          if(e.which == 82) { toggleRecording() }  // 'r'  toggle recording
          if(e.which == 73) { throttleUp() }  // 'i'  throttle up
          if(e.which == 75) { throttleDown() } // 'k'  slow down
          if(e.which == 74) { angleLeft() } // 'j' turn left
          if(e.which == 76) { angleRight() } // 'l' turn right
          if(e.which == 65) { updateDriveMode('auto') } // 'a' turn on auto mode
          if(e.which == 68) { updateDriveMode('user') } // 'd' turn on manual mode
          if(e.which == 83) { updateDriveMode('auto_angle') } // 'a' turn on auto mode
      });


      $('#pilot_select').on('change', function () {
        state.pilot = $(this).val(); // get selected value
        postPilot()
      });
      
      $('#mode_select').on('change', function () {
        updateDriveMode($(this).val());
      });
      
      $('#record_button').click(function () {
        toggleRecording();
      });
      
      $('#stop_button').click(function() {
        brake();
      });

    };


    function bindNipple(manager) {
      manager.on('start', function(evt, data) {
        state.tele.user.angle = 0
        state.tele.user.throttle = 0
        state.recording = true
        joystickLoopRunning=true;
        joystickLoop();

      }).on('end', function(evt, data) {
        joystickLoopRunning=false;
        brake()

      }).on('move', function(evt, data) {
        radian = data['angle']['radian']
        distance = data['distance']

        //console.log(data)
        state.tele.user.angle = Math.max(Math.min(Math.cos(radian)/70*distance, 1), -1)
        state.tele.user.throttle = Math.max(Math.min(Math.sin(radian)/70*distance , 1), -1)

        if (state.tele.user.throttle < .001) {
          state.tele.user.angle = 0
        }

      });
    }


    var postPilot = function(){
        data = JSON.stringify({ 'pilot': state.pilot })
        $.post(vehicleURL, data)
    }


    var updateUI = function() {
      $("#throttleInput").val(state.tele.user.throttle);
      $("#angleInput").val(state.tele.user.angle);
      $('#mode_select').val(state.driveMode);
      
      if (state.recording) {
        $('#record_button')
          .html('Stop Recording (r)')
          .removeClass('btn-info')
          .addClass('btn-warning').end()
      } else {
        $('#record_button')
          .html('Start Recording (r)')
          .removeClass('btn-warning')
          .addClass('btn-info').end()
      }
      
      //drawLine(state.tele.user.angle, state.tele.user.throttle)
    };


    var postDrive = function() {
        //Send angle and throttle values

        data = JSON.stringify({ 'angle': state.tele.user.angle, 
                                'throttle':state.tele.user.throttle, 
                                'drive_mode':state.driveMode, 
                                'recording': state.recording})
        console.log(data)
        $.post(driveURL, data)
        updateUI()
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
          } 
       }, 100)
    }

    var throttleUp = function(){
      state.tele.user.throttle = Math.min(state.tele.user.throttle + .05, 1);
      postDrive()
    };

    var throttleDown = function(){
      state.tele.user.throttle = Math.max(state.tele.user.throttle - .05, -1);
      postDrive()
    };

    var angleLeft = function(){
      state.tele.user.angle = Math.max(state.tele.user.angle - .1, -1)
      postDrive()
    };

    var angleRight = function(){
      state.tele.user.angle = Math.min(state.tele.user.angle + .1, 1)
      postDrive()
    };

    var updateDriveMode = function(mode){
      state.driveMode = mode;
      postDrive()
    };

    var toggleRecording = function(){
      state.recording = !state.recording
      postDrive()
    };

    var brake = function(i=0){
          console.log('post drive: ' + i)
          state.tele.user.angle = 0
          state.tele.user.throttle = 0
          state.recording = false
          postDrive()    


      i++    
      if (i < 5) {
        setTimeout(function () {   
          console.log('calling brake:' + i)       
          brake(i);
        }, 500)
      };


    };


    var drawLine = function(angle, throttle) {

      throttleConstant = 100
      throttle = throttle * throttleConstant
      angleSign = Math.sign(angle)
      angle = toRadians(Math.abs(angle*90))

      var canvas = document.getElementById("angleView"),
      context = canvas.getContext('2d');
      context.clearRect(0, 0, canvas.width, canvas.height);

      base={'x':canvas.width/2, 'y':canvas.height}

      pointX = Math.sin(angle) * throttle * angleSign
      pointY = Math.cos(angle) * throttle
      xPoint = {'x': pointX + base.x, 'y': base.y - pointY}

      context.beginPath();
      context.moveTo(base.x, base.y);
      context.lineTo(xPoint.x, xPoint.y);
      context.lineWidth = 5;
      context.strokeStyle = '#ff0000';
      context.stroke();
      context.closePath();

    };

    return {  load: load };

})();


function toRadians (angle) {
  return angle * (Math.PI / 180);
}