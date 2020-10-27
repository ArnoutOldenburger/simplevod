window.addEventListener("load", function(ev) {
  var buttons = document.getElementsByTagName("A");
  var selectedButton = 0;

  function selectButton(index) {
    if(buttons[selectedButton + index]) {
      selectedButton += index;
      buttons[selectedButton].focus();
    }
  }

  selectButton(0);

  window.addEventListener("keydown", function(ev) {
    if(ev.keyCode == 13) {
      if(buttons[selectedButton] && buttons[selectedButton].href) {
        //window.location = buttons[selectedButton].href;
        window.location = buttons[selectedButton].href;
      }
      ev.preventDefault();
    } else if(ev.keyCode == 38) {
      selectButton(-1);
      ev.preventDefault();
    } else if(ev.keyCode == 40) {
      selectButton(1);
      ev.preventDefault();
    }
  });
});
