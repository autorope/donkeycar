$(document).ready(function(){
    var tubId = window.location.href.split('/').slice(-1)[0];

    var clips = [];
    var selectedClipIdx = 0;
    var currentFrameIdx = 0;
    var playing = null;

    var selectedClip = function() {
        return clips[selectedClipIdx];
    };

    var pause = function() {
        if (playing) {
            clearInterval(playing);
            playing = null;
        }
        updateStreamControls();
    };

    var play = function() {
        if (playing === null) {
            playing = setInterval(function(){
                currentFrameIdx ++;
                clip = selectedClip();
                if (clip && currentFrameIdx >= clip.frames.length) {
                    currentFrameIdx = 0;
                    clearInterval(playing);
                    playing = null;
                    updateStreamControls();
                }
                updateStreamImg();
                updatePreviewProgress();
            }, 1000/$('#preview-speed').val());
        }
        updateStreamControls();
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
        var curFrame = selectedClip().frames[currentFrameIdx];
        var frameIndex = curFrame['_index'];
        var imagePath = curFrame['cam/image_array'];
        $('#img-preview').attr('src', '/tub_data/' + tubId + '/' + imagePath);
        $('#cur-frame').text(frameIndex);
        var angle = curFrame["user/angle"];
        var steeringPercent = Math.round(Math.abs(angle) * 100) + '%';
        var steeringRounded = angle.toFixed(2)
        $('.steering-bar .progress-bar').css('width', '0%').html('');
        if(angle < 0) {
            $('#angle-bar-backward').css('width', steeringPercent).html(steeringRounded)
        }
        if (angle > 0) {
            $('#angle-bar-forward').css('width', steeringPercent).html(steeringRounded)
        }
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
            $('tbody#clips').append('<tr class="' + clz + '"><td>' + playBtnOfClip(i) + '</td><td>' + thumnailsOfClip(i) + '</td><td>' + checkboxOfClip(i) + '</td></tr>');
            $('#mark-to-delete-' + i).click(function() {toggleMarkToDelete(i);});
            $('#play-clip-' + i).click(function() {playClipBtnClicked(i);});
            $('img#clipThumbnail').click(function() {clipThumbnailClicked(this);});
        });
    };

    var playBtnOfClip = function(clipIdx) {
        return '<button type="button" class="btn btn-xs" id="play-clip-' + clipIdx + '"> <span class="glyphicon glyphicon-play"></span>&nbsp; </button>';
    };

    var checkboxOfClip = function(clipIdx) {
        var frames = clips[clipIdx].frames;
        if (clips[clipIdx].markedToDelete) {
            return '<input type="checkbox" id="mark-to-delete-' + clipIdx + '" checked />';
        } else {
            return '<input type="checkbox" id="mark-to-delete-' + clipIdx + '"/>';
        }
    };

    var thumnailsOfClip = function(clipIdx) {
        var frames = clips[clipIdx].frames;
        var html = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15].map(function(i) {
            return Math.round(frames.length/16*i);
        })
        .map(function(frameIdx) {
            var frame = frames[frameIdx];
            var imagePath = frame['cam/image_array'];
            return '<img class="clip-thumbnail" id="clipThumbnail" data-clip="' + clipIdx + '" data-frame="' + frameIdx + '" src="/tub_data/' + tubId + '/' + imagePath + '" />';
        })
        .join('');

        if (clipIdx === selectedClipIdx) {
            html += previewProgress();
        }
        
        return html;
    };

    var previewProgress = function() {
        return '\
            <div class="progress">\
              <div id="preview-progress" class="progress-bar" role="progressbar" aria-valuenow="0"\
              aria-valuemin="0" aria-valuemax="100" style="width:0%">\
              </div>\
            </div>';
    };

    var updatePreviewProgress = function() {
        var progress = currentFrameIdx*100/selectedClip().frames.length;
        $('#preview-progress').css('width', progress+'%').attr('aria-valuenow', progress);
    };


    // UI event handlers
    var playBtnClicked = function(event) {
        if (playing) {
            pause();
        } else {
            play();
        }
    };

    var rewindBtnClicked = function(event) {
        currentFrameIdx -= 10;
        if (currentFrameIdx < 0) {
            currentFrameIdx = 0;
        }
        updateStreamImg();
    };

    var fforwardBtnClicked = function(event) {
        currentFrameIdx += 100; // 10 frames per second
        if (currentFrameIdx >= selectedClip().frames.length) {
            currentFrameIdx = selectedClip().frames.length-1;
        }
        updateStreamImg();
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

    var playClipBtnClicked = function(clipIdx) {
        pause();
        selectedClipIdx = clipIdx;
        currentFrameIdx = 0;
        play();
        updateClipTable();
    };

    var submitBtnClicked = function() {
        $('button#submit').prop('disabled', true);
        var clipsToKeep = clips.filter(function(clip) {
            return !clip.markedToDelete;
        })
        .map(function(clip) {
            return clip.frames;
        });

        $.ajax({
            type: 'POST',
            url: '/api/tubs/' + tubId,
            data: JSON.stringify({clips: clipsToKeep}),
            contentType: "application/json",
            dataType: 'json',
            complete: function() {
                location.reload();
            }
        });
    }

    var clipThumbnailClicked = function(el) {
        var targetClip = parseInt(el.getAttribute("data-clip"), 10);
        var targetFrame = parseInt(el.getAttribute("data-frame"), 10);
        //console.log("C: " + targetClip + " F: " + targetFrame);
        var wasPlaying = false;
        if(playing) {
            wasPlaying = true;
            pause();
        }
        selectedClipIdx = targetClip;
        currentFrameIdx = targetFrame;

        updateClipTable();
        updatePreviewProgress();
        updateStreamImg();

        if (wasPlaying) {
            play();
        }

    };
    
    var previewSpeedChanged = function() {
        // If playing then update the play speed.
        if (playing) {
            pause();
            play();
        }
    };
        
    getTub();

    $('button#play-stream').click(playBtnClicked);
    $('button#split-stream').click(splitBtnClicked);
    $('button#rewind-stream').click(rewindBtnClicked);
    $('button#fforward-stream').click(fforwardBtnClicked);
    $('button#submit').click(submitBtnClicked);
    $('select#preview-speed').change(previewSpeedChanged);
    $(document).keydown(function(e) {
        switch(e.which) {
            case 32: // space
                playBtnClicked();
                break;

            case 66: // 'b'
                rewindBtnClicked();
                break;

            case 70: // 'f'
                fforwardBtnClicked();
                break;

            case 67: // 'c'
                splitBtnClicked();
                break;

            default: return; // exit this handler for other keys
        }
        e.preventDefault(); // prevent the default action (scroll / move caret)
    });
});
