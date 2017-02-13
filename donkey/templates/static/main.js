

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

        angle = Math.max(Math.min(Math.cos(radian), 1), -1)
        throttle = Math.max(Math.min(Math.sin(radian), 1), -1)
        
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
        throttle = Math.min(throttle + .05, 1);
        postDrive()
        };

    var throttleDown = function(){
        //Bind a function to capture the coordinates of the click.
        throttle = Math.max(throttle - .05, -1);
        postDrive()
    };

    var angleLeft = function(){
      //Bind a function to capture the coordinates of the click.
      angle = Math.max(angle - .1, -1)
      postDrive()
    };

    var angleRight = function(){
      //Bind a function to capture the coordinates of the click.
      angle = Math.min(angle + .1, 1)
      postDrive()
    };

    var updateDriveMode = function(mode){
      //Bind a function to capture the coordinates of the click.
      driveMode = mode;
      postDrive()
    };


    return {  load: load };
})();
