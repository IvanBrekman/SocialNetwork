function showFile(e) {
    var file = e.target.files[0];
    var fr = new FileReader();

    fr.onload = (function(theFile) {
        return function(e) {
            document.getElementById('photo_img').src = e.target.result;
        };
    })(file);

    fr.readAsDataURL(file);
  }
