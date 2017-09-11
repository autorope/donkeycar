$(document).ready(function(){
    var tubId = window.location.href.split('/').slice(-1)[0];

    var slices = [];
    var current_slice = 0;
    var playing = null;

    var getTub = function(tId, cb) {
        $.getJSON('/api/tubs/' + tId, function( data ) {
            slices = data.slices;
            cb();
        });
    };

    var updateStreamImg = function(imgId) {
        $('#img-stream').attr('src', '/tub_data/' + tubId + '/' + imgId + '_cam-image_array_.jpg');
    };

    var updateStreamControls = function() {
        if (playing) {
            $('button#play-stream').switchClass("btn-primary", "btn-danger", 100).html('<i class="glyphicon glyphicon-pause"></i>&nbsp;Pause');
        } else {
            $('button#play-stream').switchClass("btn-danger", "btn-primary", 100).html('<i class="glyphicon glyphicon-play"></i>&nbsp;Play');
        }
    };

    // UI event handlers
    var playBtnClicked = function(event) {
        if (playing) {
            clearInterval(playing);
            playing = null;
        } else {
            var i = 0;
            playing = setInterval(function(){
                $('#img-stream').attr('src', '/tub_data/' + tubId + '/' + current_slice[i] + '_cam-image_array_.jpg');
                i ++;
                i = i % current_slice.length;
            }, 30);
        }
        updateStreamControls();
    };

    getTub(tubId, function() {
        current_slice = slices[0];
        updateStreamImg(current_slice[0]);
    });

    $('button#play-stream').click(playBtnClicked);
});
