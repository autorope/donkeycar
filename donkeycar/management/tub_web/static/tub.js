$(document).ready(function(){
    var tubId = window.location.href.split('/').slice(-1)[0];

    var clips = [];
    var selectedClipIdx = 0;
    var currentFrameIdx = 0;
    var playing = null;

    var selectedClip = function() {
        return clips[selectedClipIdx];
    };

    var getTub = function(tId, cb) {
        $.getJSON('/api/tubs/' + tubId, function( data ) {
            clips = data.clips.map(function(clip) {
                return {frames: clip, markedToDelete: false};
            });
            selectedClipIdx = 0;
            updateStreamImg();
            updateClipTable();
        });
    };

    // UI elements update
    var updateStreamImg = function() {
        $('#img-stream').attr('src', '/tub_data/' + tubId + '/' + selectedClip().frames[currentFrameIdx] + '_cam-image_array_.jpg');
    };

    var updateStreamControls = function() {
        if (playing) {
            $('button#play-stream').switchClass("btn-primary", "btn-danger", 0).html('<i class="glyphicon glyphicon-pause"></i>&nbsp;Pause');
        } else {
            $('button#play-stream').switchClass("btn-danger", "btn-primary", 0).html('<i class="glyphicon glyphicon-play"></i>&nbsp;Play');
        }
    };

    var updateClipTable = function() {
        $('tbody#clips tr').remove();
        clips.forEach(function(clip, i) {
            clz = i === selectedClipIdx ? 'active' : '';
            $('tbody#clips').append('<tr class="' + clz + '"><td>' + thumnailsOfClip(i) + '</td><td>' + deleteButtonOfClip(i) + '</td></tr>');
            $('#mark-to-delete-' + i).click(function() {toggleMarkToDelete(i);});
        });
    };

    var deleteButtonOfClip = function(clipIdx) {
        var frames = clips[clipIdx].frames;

        if (clips[clipIdx].markedToDelete) {
            return '<button class="btn btn-warning" id="mark-to-delete-' + clipIdx + '">Bring Back (' + frames.length + ')</button>';
        } else {
            return '<button class="btn btn-danger" id="mark-to-delete-' + clipIdx + '">Mark To Delete (' + frames.length + ')</button>';
        }
    };

	var thumnailsOfClip = function(clipIdx) {
        var frames = clips[clipIdx].frames;
        return [0,1,2,3,4,5,6,7].map(function(i) {
            return Math.round(frames.length/8)*i;
        })
        .map(function(frameIdx) {
            return '<img class="stream-thumbnail" src="/tub_data/' + tubId + '/' + frames[frameIdx] + '_cam-image_array_.jpg" />';
        })
        .join();
    };


    // UI event handlers
    var playBtnClicked = function(event) {
        if (playing) {
            clearInterval(playing);
            playing = null;
        } else {
            playing = setInterval(function(){
                currentFrameIdx ++;
                if (currentFrameIdx >= selectedClip().frames.length) {
                    currentFrameIdx = 0;
                    clearInterval(playing);
                    playing = null;
                    updateStreamControls();
                }
                updateStreamImg();
            }, 30);
        }
        updateStreamControls();
    };

    var splitBtnClicked = function(event) {
        if (currentFrameIdx === 0 || currentFrameIdx >= selectedClip().frames.length-1) {
            return;
        }

        clip = selectedClip();
        frames = clip.frames.splice(currentFrameIdx, clip.frames.length); // Remove frames from currentFrameIdx and assign them to another array
        selectedClipIdx++;
        clips.splice(selectedClipIdx, 0, {frames: frames, markedToDelete: false}); //Javascript's way of inserting to array at index
        currentFrameIdx = 0;

        updateStreamImg();
        updateClipTable();
    };

    var toggleMarkToDelete = function(clipIdx) {
        clips[clipIdx].markedToDelete = !clips[clipIdx].markedToDelete;
        updateClipTable();
    }

    getTub();

    $('button#play-stream').click(playBtnClicked);
    $('button#split-stream').click(splitBtnClicked);
});
