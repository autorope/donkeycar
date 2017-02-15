

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
                  'recording': "no",
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
    
      
    };



    var setBindings = function() {

      $(document).keydown(function(e) {
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

    };


    function bindNipple(manager) {
      manager.on('start end', function(evt, data) {
        state.tele.user.angle = 0
        state.tele.user.throttle = 0

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

        state.tele.user.angle = Math.max(Math.min(Math.cos(radian)/70*distance, 1), -1)
        state.tele.user.throttle = Math.max(Math.min(Math.sin(radian)/70*distance , 1), -1)

        if (state.tele.user.throttle < .001) {
          state.tele.user.angle = 0
        }


        state.recording = true

      });
    }


    var postPilot = function(){
        data = JSON.stringify({ 'pilot': state.pilot })
        $.post(vehicleURL, data)
    }


    var updateUI = function() {
      $("#throttleInput").val(state.tele.user.throttle);
      $("#angleInput").val(state.tele.user.angle);
      $('#driveMode').val(state.driveMode);
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


    // Send control updates to the server every .1 seconds.
    function joystickLoop () {           
       setTimeout(function () {    
            postDrive()

          if (joystickLoopRunning) {      
             joystickLoop();             
          } else {
            // Send zero angle, throttle and stop recording
            state.tele.user.angle = 0
            state.tele.user.throttle = 0
            state.recording = false
            postDrive() 

            function sendStop () {          
               setTimeout(function () {   
                  console.log('sendStop')
                  postDrive()         //  your code here                
                  if (!joystickLoopRunning) sendStop();      //  decrement i and call myLoop again if i > 0
               }, 3000)
            };       
            sendStop()

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