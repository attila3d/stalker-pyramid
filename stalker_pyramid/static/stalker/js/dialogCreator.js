// Stalker Pyramid a Web Base Production Asset Management System
// Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
//
// This file is part of Stalker Pyramid.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation;
// version 2.1 of the License.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

define(['dojo/domReady!'],
    function () {
        // *******************************************************************
        // DialogCaller
        //
        // Creates a dialog and also works together with stalker.submitForm and
        // updates the given field with the newly created or edited value.
        // 
        // PARAMETERS
        // 
        // dialog_id:
        //   the id of the parent dialog
        // 
        // content_creator:
        //   the content creator function for the dialog
        // 
        // data_id:
        //   if we already have some id for the data, let say if we are adding
        //   a new Sequence to a Project then this is the id or a function that
        //   returns the Project.id or if we are editing a data then this is
        //   the id or a function returning the edited data id (ex:
        //   scene_id).
        //   
        //   If the id of the edited data is not yet known you can pass a
        //   function that will return the data id.
        //
        // related_field_updater:
        //   a function object without any parameters which will update the
        //   the related field which this form is adding data to.
        // 

        // it calls a dialog which generally adds or edits a data
        // but it is not limited with that, it just calls the dialog

        var dialogCreator = function(kwargs){
            var dialog_id = kwargs.dialog_id || null,
            data_id = kwargs.data_id || function () {},
            content_creator = kwargs.content_creator,
            related_field_updater = kwargs.related_field_updater || function () {};

            if (dialog_id !== null) {
                var dialog = dijit.byId(dialog_id);
                if (dialog !== null && dialog !== undefined) {
                    dialog.destroyRecursive();
                }

                // get the data_id
                if (data_id !== null) {
                    if (typeof(data_id) === 'function') {
                        dialog = content_creator(data_id());
                    } else {
                        dialog = content_creator(data_id);
                    }
                } else {
                    dialog = content_creator();
                }

                // set the field updater
                dialog.set(
                    'related_field_updater',
                    related_field_updater
                );

                // show the dialog
                //dialog.show();

                return dialog;
            }

        };

        return dialogCreator;
    });

