

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
                  'lag': 0,
                  'controlMode': 'joystick'
                  }

    var joystick_options = {}
    var joystickLoopRunning=false;
    
    var gammaStart;   

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
      
      if (window.DeviceOrientationEvent) {
        window.addEventListener("deviceorientation", handleOrientation);
        deviceOrientationLoop();
      } else {
        console.log("Device Orientation not supported by browser.");
      }
      
    };



    var setBindings = function() {

      $(document).keydown(function(e) {
          if(e.which == 32) { toggleBrake() }  // 'space'  brake
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
      
      $('#brake_button').click(function() {
        toggleBrake();
      });
      
      $('input[type=radio][name=controlMode]').change(function() {
          if (this.value == 'joystick') {
            state.controlMode = "joystick";
            console.log('joystick mode');
            $('#joystick-column').css('display', 'block');
          }
          else if (this.value == 'tilt') {
            console.log('tilt mode')
            state.controlMode = "tilt";
            $('#joystick-column').css('display', 'none');
          }
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
      
      var throttle_percent = Math.round(Math.abs(state.tele.user.throttle) * 100) + '%';
      var steering_percent = Math.round(Math.abs(state.tele.user.angle) * 100) + '%';
      
      $('#throttle_label').html(state.tele.user.throttle.toFixed(2));
      $('#steering_label').html(state.tele.user.angle.toFixed(2));
      
      if(state.tele.user.throttle < 0) {
        $('#throttle-bar-backward').css('width', throttle_percent)
        $('#throttle-bar-forward').css('width', '0%')
      } 
      else if (state.tele.user.throttle > 0) {
        $('#throttle-bar-backward').css('width', '0%')
        $('#throttle-bar-forward').css('width', throttle_percent)
      } 
      else {
        $('#throttle-bar-forward').css('width', '0%')
        $('#throttle-bar-backward').css('width', '0%')
      }
      
      if(state.tele.user.angle < 0) {
        $('#angle-bar-backward').css('width', steering_percent)
        $('#angle-bar-forward').css('width', '0%')
      } 
      else if (state.tele.user.angle > 0) {
        $('#angle-bar-backward').css('width', '0%')
        $('#angle-bar-forward').css('width', steering_percent)
      } 
      else {
        $('#angle-bar-forward').css('width', '0%')
        $('#angle-bar-backward').css('width', '0%')
      }
      
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
      
      if (state.brakeOn) {
        $('#brake_button')
          .html('Start Vehicle')
          .removeClass('btn-danger')
          .addClass('btn-success').end()
      } else {
        $('#brake_button')
          .html('Stop Vehicle')
          .removeClass('btn-success')
          .addClass('btn-danger').end()
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

          if (joystickLoopRunning && state.controlMode == "joystick") {      
             joystickLoop();             
          } 
       }, 100)
    }
    
    // Control throttle and steering with device orientation
    function handleOrientation(event) {
      // if(state.controlMode != "tilt"){
      //   return;
      // }
      
      var alpha     = event.alpha;
      var beta     = event.beta;
      var gamma    = event.gamma;
      
      $('#alpha').html(alpha);
      $('#beta').html(beta);
      $('#gamma').html(gamma);

      if (beta == null || gamma == null) {
        return;
      }
      
      if(!gammaStart && gamma) {
        gammaStart = gamma;
      }
      
      $('#gammaStart').html(gammaStart);
      
      var newThrottle = gammaToThrottle(gamma);
      var newAngle = betaToSteering(beta, gamma);
    
      // prevent unexpected switch between full forward and full reverse 
      // when device is parallel to ground
      if (state.tele.user.throttle > 0.9 && newThrottle <= 0) {
        newThrottle = 1.0
      }
      
      if (state.tele.user.throttle < -0.9 && newThrottle >= 0) {
        newThrottle = -1.0
      }
      
      state.tele.user.throttle = newThrottle;
      state.tele.user.angle = newAngle;
      previousGamma = gamma;
      
    }
    
    function deviceOrientationLoop () {           
       setTimeout(function () {    
          if(!state.brakeOn){
            postDrive()
          }
          
          deviceOrientationLoop(); 
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
    
    var toggleBrake = function(){
      state.brakeOn = !state.brakeOn;
      gammaStart = null;
      
      if (state.brakeOn) {
        brake();
      }
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


    // var drawLine = function(angle, throttle) {
    // 
    //   throttleConstant = 100
    //   throttle = throttle * throttleConstant
    //   angleSign = Math.sign(angle)
    //   angle = toRadians(Math.abs(angle*90))
    // 
    //   var canvas = document.getElementById("angleView"),
    //   context = canvas.getContext('2d');
    //   context.clearRect(0, 0, canvas.width, canvas.height);
    // 
    //   base={'x':canvas.width/2, 'y':canvas.height}
    // 
    //   pointX = Math.sin(angle) * throttle * angleSign
    //   pointY = Math.cos(angle) * throttle
    //   xPoint = {'x': pointX + base.x, 'y': base.y - pointY}
    // 
    //   context.beginPath();
    //   context.moveTo(base.x, base.y);
    //   context.lineTo(xPoint.x, xPoint.y);
    //   context.lineWidth = 5;
    //   context.strokeStyle = '#ff0000';
    //   context.stroke();
    //   context.closePath();
    // 
    // };
 
    var betaToSteering = function(beta, gamma) {
      const deadZone = 5;
      var angle = 0.0;
      var outsideDeadZone = false;
      var controlDirection = (Math.sign(gammaStart) * -1)
      
      //max steering angle at device 35º tilt
      var fullLeft = -35.0;
      var fullRight = 35.0;
      
      //handle beta 90 to 180 discontinuous transition at gamma 90
      if (beta > 90) {
        beta = (beta - 180) * Math.sign(gamma * -1) * controlDirection
      } else if (beta < -90) {
        beta = (beta + 180) * Math.sign(gamma * -1) * controlDirection
      }
      
      if (Math.abs(beta) > 90) {
        outsideDeadZone = Math.abs(beta) < 180 - deadZone;
      } 
      else {
        outsideDeadZone = Math.abs(beta) > deadZone;
      }
      
      if (outsideDeadZone && beta < -90.0) {
        angle = remap(beta, fullLeft, (-180.0 + deadZone), -1.0, 0.0);
      } 
      else if (outsideDeadZone && beta > 90.0) {
        angle = remap(beta, (180.0 - deadZone), fullRight, 0.0, 1.0);
      } 
      else if (outsideDeadZone && beta < 0.0) {
        angle = remap(beta, fullLeft, 0.0 - deadZone, -1.0, 0);
      }
      else if (outsideDeadZone && beta > 0.0) {
        angle = remap(beta, 0.0 + deadZone, fullRight, 0.0, 1.0);
      }
      
      // sent full turn if abs(angle) > 1
      if (angle < -1) {
        angle = -1;
      } else if (angle > 1) {
        angle = 1;
      }
      
      return angle * controlDirection;
    };
    
    var gammaToThrottle = function(gamma) {
      var throttle = 0.0;
      var gamma180 = gamma + 90;
      var gammaStart180 = gammaStart + 90;
      var controlDirection = (Math.sign(gammaStart) * -1);
      
      // 10 degree deadzone around the initial position
      // 45 degrees of motion for forward and reverse
      var minForward = Math.min((gammaStart180 + (5 * controlDirection)), (gammaStart180 + (50 * controlDirection)));
      var maxForward = Math.max((gammaStart180 + (5 * controlDirection)), (gammaStart180 + (50 * controlDirection)));
      var minReverse = Math.min((gammaStart180 - (50 * controlDirection)), (gammaStart180 - (5 * controlDirection)));
      var maxReverse = Math.max((gammaStart180 - (50 * controlDirection)), (gammaStart180 - (5 * controlDirection)));
      
      //constrain control input ranges to 0..180 continuous range
      minForward = Math.max(minForward, 0);
      maxForward = Math.min(maxForward, 180);
      minReverse = Math.max(minReverse, 0);
      maxReverse = Math.min(maxReverse, 180);
      
      var throttleCalcs = "<br/>control directin: " + controlDirection + "<br/>gammaStart180: " + gammaStart180 + "<br/>minForward: " + minForward + "<br/>maxForward: " + maxForward + "<br/>minReverse: " + minReverse + "<br/>maxReverse: " + maxReverse
      $('#throttleCalcs').html(throttleCalcs);
      
      
      if(gamma180 > minForward && gamma180 < maxForward) {
        // gamma in forward range
        if (controlDirection == -1) {
          throttle = remap(gamma180, minForward, maxForward, 1.0, 0.0);
        } else {
          throttle = remap(gamma180, minForward, maxForward, 0.0, 1.0);
        }
      } else if (gamma180 > minReverse && gamma180 < maxReverse) {
        // gamma in reverse range
        if (controlDirection == -1) {
          throttle = remap(gamma180, minReverse, maxReverse, 0.0, -1.0);
        } else  {
          throttle = remap(gamma180, minReverse, maxReverse, -1.0, 0.0);
        }
      }
     
      return throttle;
    };
    
    return {  load: load };

})();


function toRadians (angle) {
  return angle * (Math.PI / 180);
}

function remap( x, oMin, oMax, nMin, nMax ){
  //range check
  if (oMin == oMax){
      console.log("Warning: Zero input range");
      return None;
  };

  if (nMin == nMax){
      console.log("Warning: Zero output range");
      return None
  }

  //check reversed input range
  var reverseInput = false;
  oldMin = Math.min( oMin, oMax );
  oldMax = Math.max( oMin, oMax );
  if (oldMin != oMin){
      reverseInput = true;
  }

  //check reversed output range
  var reverseOutput = false;  
  newMin = Math.min( nMin, nMax )
  newMax = Math.max( nMin, nMax )
  if (newMin != nMin){
      reverseOutput = true;
  };

  var portion = (x-oldMin)*(newMax-newMin)/(oldMax-oldMin)
  if (reverseInput){
      portion = (oldMax-x)*(newMax-newMin)/(oldMax-oldMin);
  };

  var result = portion + newMin
  if (reverseOutput){
      result = newMax - portion;
  }

return result;
}
