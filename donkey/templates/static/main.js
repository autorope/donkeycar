
var postLoopRunning=false;   
var sendURL = "control/"


function sendControl(angle, throttle, drive_mode, recording) {
    data = JSON.stringify({ 'angle': angle, 
                            'throttle':throttle, 
                            'drive_mode':drive_mode,
                            'recording':recording})  
           
  $.post(sendURL, data)
}


function postLoop () {           
   setTimeout(function () {    
        sendControl($('#angleInput').val(),
                    $('#throttleInput').val(),
                    'user',
                    'true')

      if (postLoopRunning) {      
         postLoop();             
      } else {
        // Send zero angle, throttle and stop recording
        sendControl(0,  0, 'user', 'false')
      }
   }, 100)
}




$( document ).ready(function() {
    console.log( "ready!" );
    velocity.bind()

  var options = {
      zone: document.getElementById('joystick_container'),                  // active zone
      color: '#668AED',
      size: 400,
  };

  var manager = nipplejs.create(options);

  bindNipple(manager);

});


function bindNipple(manager) {
  manager.on('start end', function(evt, data) {
    $('#angleInput').val(0);
    $('#throttleInput').val(0);

    if (!postLoopRunning) {
      postLoopRunning=true;
      postLoop();
    } else {
      postLoopRunning=false;
    }
    

  }).on('move', function(evt, data) {
    angle = data['angle']['radian']
    distance = data['distance']

    $('#angleInput').val(Math.round(distance * Math.cos(angle)/2));
    $('#throttleInput').val(Math.round(distance * Math.sin(angle)/2));
  });
}


$(document).keydown(function(e) {
    if(e.which == 73) {
      // 'i'  throttle up
        velocity.throttleUp()
    } 

    if(e.which == 75) {
      // 'k'  slow down
        velocity.throttleDown()
    }

    if(e.which == 74) {
      // 'j' turn left
        velocity.angleLeft()
    }

    if(e.which == 76) {
      // 'l' turn right
        velocity.angleRight()
    }

    if(e.which == 65) {
      // 'a' turn on auto mode
        velocity.updateDriveMode('auto')
    }
    if(e.which == 68) {
      // 'a' turn on auto mode
        velocity.updateDriveMode('user')
    }
      if(e.which == 83) {
      // 'a' turn on auto mode
        velocity.updateDriveMode('auto_angle')
    }
});


var velocity = (function() {
    //functions to change velocity of vehicle

    var angle = 0
    var throttle = 0
    var driveMode = 'user'
    var angleEl = "#angleInput"
    var throttleEl = "#throttleInput"
    var sendURL = "control/"

    var bind = function(data){
        //Bind a function to capture the coordinates of the click.
        $(angleEl).change(function(e) {
            sendVelocity()
        });
        $(throttleEl).change(function(e) {
            sendVelocity()
        });
    };

    var sendVelocity = function() {
        //Send angle and throttle values
        data = JSON.stringify({ 'angle': angle, 'throttle':throttle, 'drive_mode':driveMode})
        $.post(sendURL, data)
    };

    var throttleUp = function(){
        //Bind a function to capture the coordinates of the click.
        throttle = Math.min(throttle + 5, 400);
        $(throttleEl).val(throttle)
        sendVelocity()
        };

    var throttleDown = function(){
        //Bind a function to capture the coordinates of the click.
        throttle = Math.max(throttle - 10, -200);
        $(throttleEl).val(throttle);
        sendVelocity()
    };

    var angleLeft = function(){
      //Bind a function to capture the coordinates of the click.
      angle = Math.max(angle - 10, -90)
      $(angleEl).val(angle);
      sendVelocity()
    };

    var angleRight = function(){
      //Bind a function to capture the coordinates of the click.
      angle = Math.min(angle + 10, 90)
      $(angleEl).val(angle);
      sendVelocity()
    };

    var updateDriveMode = function(mode){
      //Bind a function to capture the coordinates of the click.
      driveMode = mode;
      $('#driveMode').val(mode);
      sendVelocity()
    };

    return {
                bind: bind,
                throttleUp: throttleUp,
                throttleDown: throttleDown,
                angleLeft: angleLeft,
                angleRight: angleRight,
                sendVelocity: sendVelocity,
                updateDriveMode: updateDriveMode
            };
})();
