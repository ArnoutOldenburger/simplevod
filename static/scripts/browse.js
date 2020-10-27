$(document).ready(function(){
    alert('document ready');

    $( window ).resize(function() {
        updateScale();
    });
    updateScale();
  
    selectButton(0);
    
    $(document).keydown(function(e){
        alert(e.keyCode);      

    });
    
});

function updateScale() {
    alert('updateScale');

    body = document.getElementsByTagName("BODY")[0];
    var xScale = window.innerWidth / 720;
    var yScale = window.innerHeight / 576;
    body.style.webkitTransformOrigin = "0 0";
    body.style.webkitTransform = "scale(" + xScale + ", " + yScale + ")";
}

function selectButton(index) {
    alert('selectButton');  		
}



