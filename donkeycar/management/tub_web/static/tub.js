$(document).ready(function(){
    var imgs = ['263_cam-image_array_.jpg', '42_cam-image_array_.jpg', ' 597_cam-image_array_.jpg', '763_cam-image_array_.jpg', '97_cam-image_array_.jpg'];
    var i = 0;
    setInterval(function(){
        $('#img-stream').attr('src', '/tub_data/tub_3_17-09-10/' + imgs[i%4]);
        i ++;
    }, 300);
});
