window.addEventListener("load", function(ev) {

  var buttons = document.getElementsByTagName("A");
  var topButton = 0;
  var selectedButton = 0;

  if(window.location.hash) {
    var hash = window.location.hash.substring(1);
    for(var i = 0; i < buttons.length; i++) {
      if(buttons[i].name == hash) {
        selectedButton = i;
        break;
      }
    }
  }

  function selectButton(index) {
    if(buttons[selectedButton + index]) {
      selectedButton += index;
      if(selectedButton < topButton) {
        topButton = selectedButton;
      } else if(selectedButton >= topButton + 4) {
        topButton = selectedButton - 3;
      }
      for(var i = 0; i < buttons.length; i++) {
  if(i < topButton || i >= topButton + 4) {
    buttons[i].style.display = "none";
  } else {
    buttons[i].style.display = null;
  }
      }
      buttons[selectedButton].focus();
    }
  }

  selectButton(0);

  window.addEventListener("keydown", function(ev) {
    if(ev.keyCode == 8) { // back
      window.close();
    } else if(ev.keyCode == 13) { // OK
      if(buttons[selectedButton] && buttons[selectedButton].href) {
        window.location = buttons[selectedButton].href;
      }
      ev.preventDefault();
    } else if(ev.keyCode == 37 || ev.keyCode == 38) { // left, up
      selectButton(-1);
      ev.preventDefault();
    } else if(ev.keyCode == 40 || ev.keyCode == 39) { //right, down
      selectButton(1);
      ev.preventDefault();
    }
  });
});

