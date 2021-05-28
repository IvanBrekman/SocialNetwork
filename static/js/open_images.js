// Скрипт загружает на сайт выбранное сообщение
function showFile(e) {
    let file = e.target.files[0];
    let fr = new FileReader();

    fr.onload = (function(theFile) {
        return function(e) {
            document.getElementById('photo_img').src = e.target.result;
        };
    })(file);

    fr.readAsDataURL(file);
}
