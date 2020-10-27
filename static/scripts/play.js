window.addEventListener("load", function(ev) {
  var links = document.getElementsByTagName("LINK");
  for(var i = 0; i < links.length; i++) {
    var link = links[i];
    if(link.rel == "zt6-tvod-description") {
      var location = link.href;
    } else if(link.rel == "up") {
      var returnlocation = link.href;
    }
  }
  paymentRedirect(location, returnlocation);
});

function paymentRedirect(location, returnlocation) {
  var url = "vod:tvod:" + encodeURIComponent(
    "location=" + encodeURIComponent(location) +
    "&returnlocation=" + encodeURIComponent(returnlocation));
  if(window.__openUrl__) {
    window.__openUrl__(url);
  } else {
    alert(url);
  }
}
